import logging
import shutil
from multiprocessing.pool import Pool
import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool
from distutils.util import strtobool
import argparse
import os
from os import listdir
from os.path import join, basename
from time import sleep, time
from setproctitle import setproctitle
from ftplib import FTP, error_perm
from utils.setup_tree import HarnessTree
from utils.log_setup import setup_logging
from utils.const import SCP_PARAMETERS
from settings.settings_manager import SettingsManager, DebugSettingsManager
from webservice.server.application import APP

# initialize LOGGER
setup_logging()
LOGGER = logging.getLogger(__name__)
LOGGER.debug("Logging configuration set up in %s", __name__)

LOGGER.info("Sender setup complete")

try:
    DEBUG = bool(strtobool(os.environ.get("MFSERV_HARNESS_DEBUG") or "False"))
except ValueError:
    DEBUG = False


class DifmetSender:

    _running = False
    dir_c = None
    dir_d = None
    nb_workers = None

    @classmethod
    def process(cls , max_loops=0):
        if not DEBUG:
            setproctitle("harness_difmet_sender")
        cls.nb_workers = SettingsManager.get("sendFTPlimitConn")
        # in debug mode, it is possible to set
        if DEBUG:
            pool_method = DebugSettingsManager.ftp_pool
        else:
            pool_method = Pool
        cls.pool = pool_method(processes=SCP_PARAMETERS.workers)
        counter = 0
        if not cls._running:
            LOGGER.info("Sender process starting")
            # create tree structure if necessary
            HarnessTree.setup_tree()
            cls._running = True

        while cls._running:
            counter +=1

            if counter % 10 ==0:
                LOGGER.debug("Sender process is running. "
                             "Loop number %i", counter)
            loaded = SettingsManager.load_settings()
            if loaded:
                LOGGER.debug("Settings loaded")
            # update the number of workers if necessary
            nbw = SettingsManager.get("sendFTPlimitConn")
            if nbw != cls.nb_workers:
                #wait for every upload to be finished
                cls.pool.close()
                cls.pool.join()
                #update workers
                cls.nb_workers = nbw
                cls.pool = pool_method(processes=nbw)

            # idle time
            # TODO check default value
            idle_time = SettingsManager.get("sendFTPIdle") or 10
            sleep(idle_time)

            # get settings
            cls.dir_c = dir_c = HarnessTree.get("temp_dissRequest_C")
            cls.dir_d = dir_d = HarnessTree.get("temp_dissRequest_D")
            # move back any remaining file from D to C
            for file_ in listdir(dir_d):
                shutil.move(join(dir_d, file_), dir_c)

            # get files in C
            max_files = cls.nb_workers
            list_files_c = cls.get_file_list(dir_c, max_files)
            files_to_ftp = cls.move_files(list_files_c, dir_d)

            for file_ in files_to_ftp:
                size = os.stat(file_)
                bandwidth = SettingsManager.get("bandwidth")
                if bandwidth in [None, 0]:
                    LOGGER.warning("Incorrect value for harness settings bandwidth."
                                   " Scp timeout desactivated.")
                    timeout = None
                else:
                    # conversion in Mbits/s with shift_expr << operator
                    timeout = size/bandwidth*1 << 17*SCP_PARAMETERS.timeout_buffer

                # TODO try to improve speed by connecting once and pass the FTP object.
                # might not work though because of pickle issues in multiprocessing
                # the timeout is managed at pool level, not individually
                res = cls.pool.apply_async(cls.abortable_ftp,
                                            (cls.upload_file, file_),
                                            dict(timeout=timeout))
                if DEBUG:
                    res.wait()
            if counter == max_loops:
                LOGGER.info("Performed required %i loops, exiting.", counter)
                cls.stop()

    @classmethod
    def stop(cls):
        LOGGER.info("Received request for %s process to stop looping.",
                     cls.__name__)
        cls._running = False


    @staticmethod
    def get_file_list(dirname, maxfiles):

        list_entries = os.listdir(dirname)
        list_entries = [os.path.join(dirname, entry) for entry in list_entries]
        # sort by date
        list_files = [e for e in list_entries if not os.path.isdir(e)]
        # TODO sort by priority
        list_files.sort(key=lambda x: os.stat(x).st_mtime)

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
        # TODO see the use of mode
        #mode = SettingsManager.get("dissFtpMode")
        port = SettingsManager.get("dissFtpPort")

        # try:
        #     ftp = FTP(host=hostname,user=user,passwd=password)
        #     ftp_connected = True
        # #TODO introduce exceptions
        # except error_perm:
        #     ftp = FTP()
        #     ftp.connect(hostname,port)
        #     ftp.login(user,password)
        #     ftp_connected = True
        try:
            ftp = FTP()
            ftp.connect(hostname,port)
            ftp.login(user,password)
            ftp_connected = True
        except Exception as e:
            LOGGER.exception("Couldn't connect to %s", hostname)
            ftp_connected = False
            ftp = None

        return ftp_connected, ftp


    # TODO issue with raising exception in abortable_ftp
    # see this https://stackoverflow.com/questions/6728236/exception-thrown-in-multiprocessing-pool-not-detected
    # and https://stackoverflow.com/questions/6126007/python-getting-a-traceback-from-a-multiprocessing-process/26096355#26096355
    # for more info
    @classmethod
    def abortable_ftp(cls, func, *args, **kwargs):
        timeout = kwargs.get('timeout', None)
        proc = ThreadPool(1)

        res = proc.apply_async(func, args=args)
        # size in Mbytes
        file_ = args[0]
        size = os.stat(file_).st_size / (1 << 20)
        try:
            # Wait timeout seconds for func to complete.
            upload_ok, duration = res.get(timeout)
            if not upload_ok:
                shutil.move(file_, cls.dir_c)
                LOGGER.debug("Moved file back from repertory %s to repertory %s",
                            cls.dir_d, cls.dir_c)
            else:
                LOGGER.info("File %s of size %f Mo sent to Diffmet in %f s",
                             file_, size, duration)
                os.remove(file_)
                LOGGER.debug("File %s deleted", file_)
        except multiprocessing.TimeoutError:
            LOGGER.error("Timeout of %f s exceeded for sending file %s"
                         " on staging post.", file_, timeout)
            # move the file back from D to C
            shutil.move(file_, cls.dir_c)
            LOGGER.debug("Moved file back from repertory %s to repertory %s",
                         cls.dir_d, cls.dir_c)
        proc.terminate()

    @classmethod
    def upload_file(cls, file_):
        start = time()

        # TODO exception are not thrown back
        connection_ok, ftp = cls.connect_ftp()
        if connection_ok:
            ftpdir = SettingsManager.get("dissFtpDir")
            # TODO dir existence check
            ftp.cwd(ftpdir)
            # renaming in tmp
            file_renamed = basename(file_) + ".tmp"
            ftp.storbinary('STOR ' + file_renamed, open(file_, 'rb'))
            ftp.rename(file_renamed, basename(file_))

            upload_ok = True
            ftp.quit()
        else:
            upload_ok = False

        return upload_ok, time() - start

if DEBUG and __name__ == '__main__':

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
    setup_logging()
    LOGGER = logging.getLogger("file_sender.sender")
    LOGGER.debug("Logging configuration set up in %s", "file_sender.sender")

    LOGGER.info("Sender setup complete")
    DifmetSender.process(max_loops)