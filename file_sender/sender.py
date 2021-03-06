"""
    This module processes the files in cache/C_tosend by sending it via FTP
    through n=sendFTPlimitConn process that are occuring independantly and 
    concurrently. Each FTP upload has its own timeout computed through the bandwidth
    parameter and the size of the file uploaded
"""
import argparse
import logging
import multiprocessing
import os
import shutil
import traceback
from distutils.util import strtobool
from ftplib import FTP, error_perm
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing.pool import Pool
from os import listdir, rename
from os.path import basename, join, splitext, isfile
from time import sleep, time
from re import match
from setproctitle import setproctitle
from settings.settings_manager import DebugSettingsManager, SettingsManager
from utils.const import DEBUG_TIMEOUT, ENV, TIMEOUT, TIMEOUT_BUFFER
from utils.log_setup import setup_logging
from utils.setup_tree import HarnessTree
from utils.tools import Tools

# initialize LOGGER
LOGGER = logging.getLogger(__name__)
LOGGER.debug("Logging configuration set up for %s", __name__)

try:
    DEBUG = strtobool(os.environ.get(ENV.debug) or DebugSettingsManager.get("debug"))
except ValueError:
    DEBUG = False


class DifmetSender:

    _running = False
    dir_c = None
    dir_d = None
    nb_workers = None

    @classmethod
    def process(cls , max_loops=0):
        cls.nb_workers = SettingsManager.get("sendFTPlimitConn")
        # in debug mode, it is possible to set
        pool_method = cls.get_pool_method()
        cls.pool = pool_method(processes=cls.nb_workers)
        counter = 0
        cls.setup_process()
        while cls._running:
            counter +=1

            cls.signal_loop(counter)
            cls.load_settings()
            cls.update_workers()
            # idle time
            idle_time = SettingsManager.get("sendFTPIdle")
            sleep(idle_time)

            # get settings
            cls.dir_c = dir_c = HarnessTree.get("temp_dissRequest_C")
            cls.dir_d = dir_d = HarnessTree.get("temp_dissRequest_D")
            # move back any remaining file from D to C
            cls.move_back_files()

            # get files in C
            max_files = cls.nb_workers
            list_files_c = cls.get_file_list(dir_c, max_files)
            files_to_ftp = cls.move_files(list_files_c, dir_d)

            for file_ in files_to_ftp:

                file_expired = cls.check_file_age(file_)
                if file_expired:
                    # TODO we need to find a way to update the info to the database
                    # would require looking at the file compressed though
                    Tools.remove_file(file_, "difmet archive", LOGGER)
                    continue
                size = os.stat(file_).st_size

                timeout= cls.compute_timeout(size, file_)

                # start download
                # renaming file to prevent any operation on it.
                cls.lock_file(file_)
                res = cls.pool.apply_async(cls.abortable_ftp,
                                            (cls.upload_file, file_, dir_c,dir_d),
                                            dict(timeout=timeout))

            # for testing and debugging purpose only
            cls.check_end_loop(counter, max_loops)


    @classmethod
    def move_back_files(cls):
        for file_ in listdir(cls.dir_d):
            # move back every file except those who are still in transfer
            if not splitext(file_)[1] == ".lock":
                try:
                    shutil.move(join(cls.dir_d, file_), cls.dir_c)
                # to avoid concurrent issue
                except FileNotFoundError:
                    pass

    @classmethod
    def check_end_loop(cls, counter, max_loops):
        # for testing and debugging purpose only
        if counter == max_loops:
            LOGGER.info("Performed required %i loops, exiting.", counter)
            cls.stop()

    @staticmethod
    def get_pool_method():
        if DEBUG:
            pool_method = DebugSettingsManager.ftp_pool
        else:
            pool_method = Pool

        return pool_method

    @staticmethod
    def check_file_age(filename):
        time_limit = SettingsManager.get("keepFileTimeSender") or None
        if time_limit is not None:
            check = (time() - os.stat(filename).st_mtime) > time_limit
        else:
            check = False
        return check


    @classmethod
    def setup_process(cls):
        if not cls._running:
            setup_logging()
            LOGGER = logging.getLogger(__name__)
            LOGGER.info("Sender process starting")
            # create tree structure if necessary
            HarnessTree.setup_tree()
            cls._running = True

    @staticmethod
    def signal_loop(counter):
        if counter % 10 ==0:
            LOGGER.debug("Sender process is running. "
                         "Loop number %i", counter)
            if DEBUG:
                LOGGER.warning("DEBUG mode activated.")

    @staticmethod
    def load_settings():
        loaded = SettingsManager.load_settings()
        if loaded:
            LOGGER.debug("Settings loaded")

    @classmethod
    def update_workers(cls):
        # update the number of workers if necessary
        nbw = SettingsManager.get("sendFTPlimitConn")
        if nbw != cls.nb_workers:
            #wait for every upload to be finished
            cls.pool.close()
            cls.pool.join()
            #update workers
            cls.nb_workers = nbw
            cls.pool = pool_method(processes=nbw)


    @staticmethod
    def compute_timeout(required_bandwith, file_):
        # compute timeout
        bandwidth = SettingsManager.get("bandwidth")
        if bandwidth in [None, 0]:
            LOGGER.warning("Incorrect value for harness settings bandwidth. "
                           "ftp timeout set to default TIMEOUT %i s for file %s.",
                            TIMEOUT, file_)
            timeout = TIMEOUT
        elif DEBUG:
            timeout = DEBUG_TIMEOUT
            LOGGER.debug("Ftp debug timeout set to %s s for file %s.",
                         timeout, file_)
        else:
            # conversion in Mbits/s with shift_expr << operator
            timeout = (required_bandwith/(1 << 17))/bandwidth + TIMEOUT_BUFFER
            LOGGER.debug("Ftp timeout computed to %s s for file %s.",
                         timeout, file_)

        return timeout


    @classmethod
    def stop(cls):
        LOGGER.info("Received request for %s process to stop looping.",
                     cls.__name__)
        cls._running = False
        cls.pool.terminate()


    @classmethod
    def get_file_list(cls, dirname, maxfiles):

        overflow = SettingsManager.get("SenderOverflow")

        list_entries = os.listdir(dirname)

        # don't takes files into account if they end by .tmp

        list_entries = [item for item in list_entries if match(r".*\.tmp$", item) is None]

        list_entries = [os.path.join(dirname, entry) for entry in list_entries]
        # sort by date
        list_files = [e for e in list_entries if not os.path.isdir(e)]
        list_files.sort(key=lambda x: os.stat(x).st_mtime)
        if overflow is not None and len(list_files) > overflow:
            LOGGER.warning("%s repertory is overflowing. "
                         "Number of files %i over the limit %i",
                         cls.dir_c, len(list_files), overflow)
        list_files = list_files[:maxfiles]

        return list_files

    @staticmethod
    def move_files(list_files, out_dir):

        updated_list = []

        for file_ in list_files:
            LOGGER.debug("Moving file %s in %s", file_, out_dir)
            shutil.move(file_, out_dir)
            name = basename(file_)
            updated_list.append(os.path.join(out_dir, name))

        return updated_list




    @staticmethod
    def connect_ftp():

        hostname = SettingsManager.get("dissHost")
        user = SettingsManager.get("dissFtpUser")
        password = SettingsManager.get("dissFtpPasswd")
        port = SettingsManager.get("dissFtpPort")

        try:
            ftp = FTP()
            ftp.connect(hostname,port)
            ftp.login(user,password)
            if SettingsManager.get("dissFtpMode") == "active":
                ftp.set_pasv(False)
                LOGGER.debug("FTP mode set to active")
            elif SettingsManager.get("dissFtpMode") == "passive":
                ftp.set_pasv(True)
                LOGGER.debug("FTP mode set to passive")
            ftp_connected = True
        except Exception as e:
            LOGGER.exception("Couldn't connect to %s", hostname)
            ftp_connected = False
            ftp = None

        return ftp_connected, ftp


    @classmethod
    def abortable_ftp(cls, func, *args, **kwargs):

        try:
            timeout = kwargs.get('timeout', None)
            # size in Mbytes
            # get file name + ".lock" extension
            original_file, dir_c, dir_d  = args
            file_ = original_file + ".lock"
            size = os.stat(file_).st_size / (1 << 20)
            connection_ok, ftp = cls.connect_ftp()
            if connection_ok:
                proc = ThreadPool(1)
                res = proc.apply_async(func, args=(original_file,ftp,))
                try:
                    # Wait timeout seconds for func to complete.
                    upload_ok, duration = res.get(timeout)
                    file_ = cls.unlock_file(file_)
                    if not upload_ok:
                        shutil.move(file_, dir_c)
                        LOGGER.debug("Moved file back from repertory %s to repertory %s",
                                    dir_d, dir_c)
                    else:
                        LOGGER.info("File %s of size %f Mo sent to Diffmet in %f s",
                                    file_, size, duration)
                        Tools.remove_file(file_, "difmet archive", LOGGER)
                    ftp.quit()
                except multiprocessing.TimeoutError:
                    ftp.close()
                    proc.terminate()
                    
                    LOGGER.error("Timeout of %f s exceeded for sending file %s"
                                " on difmet. Checking upload.", timeout, original_file)
                    _, ftp = cls.connect_ftp()
                    upload_ok = cls.check_transfer(basename(original_file), ftp)
                    if upload_ok:
                        LOGGER.warning("Process hit the timeout but "
                                    "file %s of size %f Mo was still sent to Diffmet",
                                    file_, size)
                        Tools.remove_file(file_, "difmet archive", LOGGER)
                    else:
                        file_ = cls.unlock_file(file_)
                        LOGGER.error("FTP upload of %s s failed.", file_)
                        # move the file back from D to C
                        shutil.move(file_, dir_c)
                        LOGGER.debug("Moved file back from repertory %s to repertory %s",
                                    dir_d, dir_c)
                except Exception as exc:
                    file_ = cls.unlock_file(file_)
                    trace = ''.join(traceback.format_exception(type(exc),
                                    exc, exc.__traceback__))
                    LOGGER.error("Error when uploading file %s with "
                                "trace :\n %s", file_, trace)
                    ftp.quit()
            else:
                file_ = cls.unlock_file(file_)
                LOGGER.error("Couldn't connect to FTP for uploading file %s ", file_)
                # move the file back from D to C
                shutil.move(file_, dir_c)
                LOGGER.debug("Moved file back from repertory %s to repertory %s",
                            dir_d, dir_c)
            
            proc.terminate()
        except Exception as exc:
            trace = ''.join(traceback.format_exception(type(exc),
                            exc, exc.__traceback__))
            LOGGER.error("Error when uploading file %s with "
                        "trace :\n %s", file_, trace)

    @classmethod
    def check_transfer(cls, filename, ftp):
        #  check if file exists on remote server
        ftpdir = SettingsManager.get("dissFtpDir")
        ftp.cwd(ftpdir)
        if filename in [name for name, data in list(ftp.mlsd())]:
            upload_ok = True
        else:
            upload_ok = False
        ftp.quit()

        return upload_ok

    @staticmethod
    def unlock_file(file_):
        if splitext(file_)[1] == ".lock":
            rename(file_, file_[:-5])
            file_ = file_[:-5]
        return file_

    @staticmethod
    def lock_file(file_):
        rename(file_, file_ + ".lock")

    @classmethod
    def upload_file(cls, file_,ftp):
        upload_ok =False
        start = time()
        file_locked = file_ + ".lock"
        with open(file_locked, 'rb') as file_transfered:
            ftpdir = SettingsManager.get("dissFtpDir")
            ftp.cwd(ftpdir)
            # renaming in tmp
            file_renamed = basename(file_) + ".tmp"
            ftp.storbinary('STOR ' + file_renamed, file_transfered)
            ftp.rename(file_renamed, basename(file_))

            upload_ok = True

        return upload_ok, time() - start

if __name__ == '__main__':


    # this is used for testing and debugging purpose only. It allows to launch the process independently
    # for user specified n loops
    process_name = "harness_difmet_sender"
    setproctitle(process_name)
    parser = argparse.ArgumentParser(description='File sender process loop.')

    parser.add_argument("--loops", help=("How many loops should the process "
                                         "execute.\n "
                                         "Loop indefinitly if no value is "
                                         "provided"),
                                    type=int,
                                    nargs=1)

    args = parser.parse_args()
    if args.loops:
        max_loops = args.loops[0]
    else:
        max_loops = 0

    # initialize LOGGER
    SettingsManager.load_settings()
    setup_logging()
    LOGGER = logging.getLogger("file_sender.sender")
    LOGGER.debug("Logging configuration set up for %s", "file_sender.sender")

    LOGGER.info("Sender setup complete")
    DifmetSender.process(max_loops)
