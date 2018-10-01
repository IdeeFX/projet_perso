import logging
import os
import shutil
import tarfile
import json
import re
from distutils.util import strtobool
from stat import S_ISDIR
import multiprocessing
import argparse
from time import sleep, time, strftime
from datetime import datetime, timedelta
from functools import partial
from lxml import etree
import paramiko
from setproctitle import setproctitle
from settings.settings_manager import SettingsManager, DebugSettingsManager
from utils.log_setup import setup_logging
from utils.setup_tree import HarnessTree
from utils.database import Database, Diffusion
from utils.const import (REQ_STATUS, SCP_PARAMETERS, DEBUG_TIMEOUT, PRIORITIES,
                         MAX_REGEX, DEFAULT_ATTACHMENT_NAME)
from utils.tools import Tools, Incrementator
from webservice.server.application import APP


try:
    DEBUG = bool(strtobool(os.environ.get("MFSERV_HARNESS_DEBUG") or "False"))
except ValueError:
    DEBUG = False
try:
    TEST_SFTP = bool(strtobool(os.environ.get("MFSERV_HARNESS_TEST_SFTP") or "False"))
except ValueError:
    TEST_SFTP = False


# initialize LOGGER
setup_logging()
LOGGER = logging.getLogger(__name__)
LOGGER.debug("Logging configuration set up in %s", __name__)

LOGGER.info("File Manager setup complete")

class FileOverSizeLimit(Exception):
    pass

class FileManager:
    _running = False
    dir_a = None
    dir_b = None
    dir_c = None

    @classmethod
    def process(cls, max_loops=0):
        if not DEBUG:
            setproctitle("harness_file_manager")
        counter = 0
        instr_to_process = False
        if not cls._running:
            LOGGER.info("File manager process starting")
            # create tree structure if necessary
            HarnessTree.setup_tree()
            #connect the database
            Database.initialize_database(APP)
            cls._running = True
        while cls._running:
            counter +=1
            if counter % 10 ==0:
                LOGGER.debug("File manager process is running. "
                             "Loop number %i", counter)
            loaded = SettingsManager.load_settings()
            if loaded:
                LOGGER.debug("Settings loaded")
            cls.dir_a = dir_a = HarnessTree.get("temp_dissRequest_A")
            cls.dir_b = dir_b = HarnessTree.get("temp_dissRequest_B")
            cls.dir_c = HarnessTree.get("temp_dissRequest_C")
            # TODO implémenter bypass de 8.1
            start_time = time()
            # idle time
            # TODO check default value
            idle_time = SettingsManager.get("processFileIdle") or 10
            sleep(idle_time)

            # get the maxDirectiveFile first files
            # TODO check default value
            max_direc_files = SettingsManager.get("processFileDPmax") or 10
            list_files_a = cls.get_file_list(dir_a, maxfiles=max_direc_files)
            instruction_files = cls.move_files(list_files_a, dir_b)

            if instruction_files == []:
                if instr_to_process:
                    LOGGER.debug("No instruction file to process, moving on.")
                    instr_to_process = False
                continue
            else:
                LOGGER.debug("Fetched %i instruction files from %s",
                             len(instruction_files), dir_a)
                instr_to_process = True


            # process instruction files
            diss_instructions = dict()
            all_files_fetched = []
            for file_to_process in instruction_files:
                # empty the list, one item at a time
                process_ok, instructions, files_fetched = cls.process_instruction_file(
                    file_to_process)

                if process_ok:
                    req_id = instructions["req_id"]
                    hostname = instructions["hostname"]
                    diss_instructions[req_id+hostname] = instructions
                    all_files_fetched += [item for item in files_fetched if
                                         item not in all_files_fetched]

            # process files fetched
            for file_path in all_files_fetched:

                filename = os.path.basename(file_path)
                requestId_list = Database.get_id_list_by_filename(filename)

                # no reference
                if requestId_list == []:
                    os.remove(file_path)
                    LOGGER.debug("Deleting orphan file %s", file_path)
                    continue

                # purge requestId_list or req_id that are not in
                # diss_instructions keys. That is to prevent trying to find
                # an instruction file related to a file that has been processed
                # by a previous request

                requestId_list = [item for item in requestId_list
                                  if item in diss_instructions.keys()]

                LOGGER.debug("Processing downloaded file %s linked to "
                            "requests %s", file_path, requestId_list)

                diff_manager = DiffMetManager(
                    requestId_list, file_path, diss_instructions)
                # rename files according to regex
                diff_manager.rename()
                # package the archive
                diff_manager.compile_archive()


            # cleaning instruction files
            for file_ in instruction_files:
                try:
                    os.remove(file_)
                    LOGGER.debug("Instruction file %s deleted",
                                 file_)
                # file either was moved back to repertory A or deleted
                except FileNotFoundError:
                    pass

            # cleaning other files
            for file_ in os.listdir(dir_b):
                file_path = os.path.join(dir_b, file_)
                try:
                    os.remove(file_)
                    LOGGER.debug("Orphan file %s deleted",
                                    file_path)
                except FileNotFoundError:
                    pass
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
        list_files = [
            entry for entry in list_entries if not os.path.isdir(entry)]
        list_files.sort(key=lambda x: os.stat(x).st_mtime)

        list_files = list_files[:maxfiles]

        return list_files

    @staticmethod
    def move_files(list_files, out_dir):

        updated_list = []

        for file_ in list_files:
            LOGGER.debug("Moving file %s in %s", file_, out_dir)
            shutil.move(file_, out_dir)
            basename = os.path.basename(file_)
            updated_list.append(os.path.join(out_dir, basename))

        return updated_list

    @staticmethod
    def check_file_age(filename):
        time_limit = SettingsManager.get("keepFileTime") or None
        if time_limit is not None:
            check = (time() - os.stat(filename).st_mtime) > time_limit
        else:
            check = False
        return check

    @classmethod
    def process_instruction_file(cls, file_to_process):

        processed = False
        files_fetched = []

        with open(file_to_process, "r") as file_:
            info_file = json.load(file_)

        # get full_id
        req_id = info_file.get("req_id")
        hostname = info_file.get("hostname")
        full_id = req_id + hostname

        file_expired = cls.check_file_age(file_to_process)
        if file_expired:
            LOGGER.warning("%s instruction file discarded "
                           "because it is over expiration date "
                           "according to keepfiletime settings "
                           "parameter", file_to_process)
            Database.update_field_by_query("requestStatus", REQ_STATUS.failed,
                                           **dict(fullrequestId=full_id))
        else:
            # get URI
            uri = info_file.get("uri")
            # fetch files on staging post
            processed, files_fetched = cls.fetch_files(req_id, hostname, uri)
            # if a file couldn't be gathered, dissemination is failed and
            # instruction file deleted
            if not processed:
                LOGGER.error("Couldn't fetch files from openwis staging post for"
                             " instruction file %s."
                             " Proceeding to next instruction file.",
                             file_to_process)
                # check if database status is at failed. If yes, instruction file is deleted.
                # if not, it sent back to A repertory to be processed again
                if Database.get_request_status(full_id) == REQ_STATUS.failed:
                    os.remove(file_to_process)
                else:
                    shutil.move(file_to_process, cls.dir_a)

            # TODO check with benjamin that we are not moving files TWICE
            # else:
            #     # moving instruction file to B repertory
            #     shutil.move(file_to_process, cls.dir_b)

        return processed, info_file, files_fetched


    @staticmethod
    def fetch_files(req_id, hostname, uri):

        connection_pointer = ConnectionPointer(req_id, hostname)
        fetch_ok, files_fetched = connection_pointer.fetch(uri)

        return fetch_ok, files_fetched


class ConnectionPointer:

    def __init__(self, req_id, hostname):

        # path to file on staging post
        self.staging_path = SettingsManager.get("openwisStagingPath") or ""
        self.hostname = SettingsManager.get("openwisHost") or hostname
        self.user = SettingsManager.get("openwisSftpUser") or None
        self.password = SettingsManager.get("openwisSftpPassword") or None
        self.port = SettingsManager.get("openwisSftpPort") or None
        self.req_id = req_id + hostname

    def update_filename(self, filename):
        # fetch database
        database = Database.get_database()

        # get the base record to duplicate
        with Database.get_app().app_context():
            base_record = Diffusion.query.filter_by(
            fullrequestId=self.req_id).first()

            if base_record.original_file is None:
                # if there is only the one record created by
                # receiver module, job is done
                base_record.original_file = filename
                database.session.commit()
            # otherwise, we create a new record
            else:
                diffusion = Diffusion(diff_externalid=Tools.generate_random_string(),
                                    fullrequestId=base_record.fullrequestId,
                                    original_file=filename,
                                    requestStatus=base_record.requestStatus,
                                    message=base_record.message,
                                    Date=base_record.Date,
                                    rxnotif=base_record.rxnotif)

                database.session.add(diffusion)
                database.session.commit()

    def fetch(self, file_uri):

        fetch_ok = False

        dir_path = os.path.join(self.staging_path, file_uri)
        destination_dir = HarnessTree.get("temp_dissRequest_B")

        # move the file if hostname is localhost. Sftp it otherwise
        # TODO prendre en considération Harnessdiss.synchro en 8.5
        files_fetched = []
        if self.hostname == "localhost" and \
           os.path.isdir(dir_path) and \
           not TEST_SFTP:
            for item in os.listdir(dir_path):
                file_path = os.path.join(dir_path, item)
                # folders are ignored
                if os.path.isdir(file_path):
                    files_fetched.append(file_path)
                    continue
                destination_path = os.path.join(destination_dir, item)
                # if the file has already been fetched by a previous instruction file,
                # we don't do it again
                if not os.path.isfile(destination_path):
                    shutil.copy(file_path, destination_path)
                self.update_filename(item)
                files_fetched.append(file_path)
            fetch_ok = True
        elif self.hostname == "localhost" and not os.path.isdir(dir_path):
            LOGGER.error("Staging post path %s is not a directory. "
                         "Dissemination failed", dir_path)
            Database.update_field_by_query("requestStatus", REQ_STATUS.failed,
                                           **dict(fullrequestId=self.req_id))
            fetch_ok = False
        else:
            fetch_ok, files_fetched = self.scp_dir(dir_path, destination_dir)

        return fetch_ok, files_fetched

    def unzip_file(self, list_files):
        # TODO obviously...
        raise NotImplementedError
        return new_path

    # @staticmethod
    # def _scp_file(sftp, *args,**kwargs):
    #         # ssh = paramiko.SSHClient()
    #         # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    #         # ssh.connect(**kwargs)
    #         # sftp = ssh.open_sftp()
    #         sftp.get(*args)
    #         # sftp.close()
    #         # ssh.close()

    def scp_dir(self, dir_path, destination_dir):


        files_to_scp = []
        try:
            transport = paramiko.Transport((self.hostname, self.port))
            transport.connect(username=self.user, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.chdir(dir_path)
            required_bandwith = 0
            for item in sftp.listdir(dir_path):
                file_path = os.path.join(dir_path, item)
                destination_path = os.path.join(destination_dir, item)
                # if the file has already been fetched by a previous instruction file,
                # we don't do it again
                if os.path.isfile(destination_path):
                    files_to_scp.append((file_path, destination_path))
                    continue
                mode = sftp.stat(file_path).st_mode
                # ignore directories
                if S_ISDIR(mode):
                    continue
                # check for file_size
                size = sftp.stat(file_path).st_size
                max_size = SettingsManager.get("processFilesize")
                # if size > max_size, diffusion failed.
                # conversion in Mbytes with shift_expr << operator
                if max_size is not None and size > max_size*(1 << 20):
                    raise FileOverSizeLimit
                required_bandwith += size

                # if a file, get it
                LOGGER.debug('file %s found on openwis staging post',
                             file_path
                             )
                files_to_scp.append((file_path, destination_path))



            # initialize the multiprocessing manager
            if DEBUG:
                pool = DebugSettingsManager.sftp_pool(processes=SCP_PARAMETERS.workers)
                # pool = multiprocessing.dummy.Pool(processes=SCP_PARAMETERS.workers)
            else:
                pool = multiprocessing.Pool(processes=SCP_PARAMETERS.workers)
            # add job to pool
            # TODO clean up
            # scp_files = partial(self._scp_file, **connection_info)
            # results = pool.starmap_async(scp_files, files_to_scp)
            results = pool.starmap_async(sftp.get, files_to_scp)
            # compute timeout
            bandwidth = SettingsManager.get("bandwidth")
            if bandwidth in [None, 0]:
                LOGGER.warning("Incorrect value for harness settings bandwidth."
                               " Scp timeout desactivated.")
                # TODO can stop the process ! Be careful
                timeout = None
            elif DEBUG:
                timeout = DEBUG_TIMEOUT
                LOGGER.debug("Sftp debug timeout set to %s s", timeout)
            else:
                # conversion in Mbits/s with shift_expr << operator
                timeout = required_bandwith/bandwidth*1 << 17*SCP_PARAMETERS.timeout_buffer
                LOGGER.debug("Sftp timeout computed to %s s", timeout)
            # start download
            try:
                LOGGER.debug("Attempting download of %i files, for a total size of "
                             " %f. Timeout is fixed at %s s.", len(
                                 files_to_scp),
                             required_bandwith, timeout)
                results.get(timeout=timeout)
                scp_success = True
            except multiprocessing.TimeoutError:
                LOGGER.error(
                    "Timeout exceeded for fetching files on staging post.")
                scp_success = False

            # check download success and unzip if necessary then update database
            for remote_path, local_path in files_to_scp:
                if os.path.isfile(local_path):
                    LOGGER.debug('file %s downloaded in repertory %s',
                                 remote_path,
                                 os.path.dirname(local_path)
                                 )
                    # unzip and gets new name
                    if os.path.basename(local_path) == "tmp.zip":
                        local_path = self.unzip_file(local_path)
                    scp_success = True and scp_success
                else:
                    LOGGER.error("Download of file %s in repertory %s failed.", remote_path,
                                 os.path.dirname(local_path)
                                 )
                    scp_success = False

            sftp.close()

        # TODO exception when no staging post dir
        except (paramiko.SSHException,
                paramiko.ssh_exception.NoValidConnectionsError):
            LOGGER.exception("Couldn't connect to %s", self.hostname)
            scp_success = False
        except FileOverSizeLimit:
            LOGGER.exception('file %s found on openwis staging post'
                'is over the size limit %f. Dissemination '
                'failed',
                file_path,
                max_size
                )
            Database.update_field_by_query("requestStatus", REQ_STATUS.failed,
                                            **dict(fullrequestId=self.req_id))
            scp_success = False
        except FileNotFoundError:
            LOGGER.exception('Incorrect path %s for openwis staging post'
                'Dissemination failed',
                dir_path
                )
            Database.update_field_by_query("requestStatus", REQ_STATUS.failed,
                                            **dict(fullrequestId=self.req_id))
            scp_success = False


        # update database
        files_downloaded = []
        if scp_success:
            for  _, local_path in files_to_scp:
                self.update_filename(os.path.basename(local_path))
                files_downloaded.append(local_path)


        return scp_success, files_downloaded


class DiffMetManager:

    def __init__(self, id_list, file_path, instructions_dict):

        self.id_list = id_list
        self.original_filename = os.path.basename(file_path)
        self.original_file_path = file_path
        self.new_filename = None
        self.new_file_path = None
        self.instructions = dict()
        # prune the instructions_dict from info we don't need.
        # better safe than sorry
        for req_id in id_list:
            if req_id in instructions_dict.keys():
                self.instructions[req_id] = instructions_dict[req_id]
        self.incr = Incrementator.get_incr()
        self.dir_b = FileManager.dir_b
        self.dir_c = FileManager.dir_c

    def _get_instr(self, req_id, key):
        return self.instructions[req_id][key]

    def _rename_by_regex(self, old_filename, reg, repl):

        # compile regex
        # [:$requestID]: variable contenant le requestId associé au fichier à télécharger.
        # [:$hostname]: Adresse IP ou hostname associé au requestId.
        # [ :$sequence] : nombre sur 5 digits s’incrémentant à chaque appel de 00000 à 99999 permettant une unicité.
        # [:$YYYY] : année en tant que nombre sur 4 chiffres.
        # [:$MM] : mois de 01 à 12
        # [:$DD] : jour du mois format 01 à 31
        # [:$HH] : heure au format 24 h de 00 à 23
        # [:$mm] : minute de 00 à 59
        # [:$SS] : seconde de 00 à 59
        # if multiple id, we take the first
        req_id = self.id_list[0]
        repl = repl.replace("[:$requestID]", req_id)
        repl = repl.replace(
            "[:$hostname]", self._get_instr(req_id, "hostname"))

        date_recept = self._get_instr(req_id, "date")
        # date_recept is in format YYYYMMDDHHmmSS therefore
        repl = repl.replace("[:$YYYY]", date_recept[:4])
        repl = repl.replace("[:$MM]", date_recept[4:6])
        repl = repl.replace("[:$DD]", date_recept[6:8])
        repl = repl.replace("[:$HH]", date_recept[8:10])
        repl = repl.replace("[:$mm]", date_recept[10:12])
        repl = repl.replace("[:$SS]", date_recept[12:14])
        repl = repl.replace("[:$sequence]", self.incr)

        old_path = os.path.join(self.dir_b, old_filename)
        new_filename = re.sub(reg, repl, old_filename)
        new_path = os.path.join(self.dir_b, new_filename)

        shutil.move(old_path, new_path)
        LOGGER.debug("Renaming file %s in %s",
                     old_filename, new_filename)
        self.new_file_path = new_path
        return new_filename

    def rename(self):

        regex_settings = [SettingsManager.get(
            "fileRegex%i" % i, {}) for i in range(1, MAX_REGEX+1)]

        new_filename = self.original_filename
        for idx, regex_instruction in enumerate(regex_settings):
            reg = regex_instruction.get("pattern_in", None)
            repl = regex_instruction.get("pattern_out", None)

            if None not in (reg, repl):
                new_filename = self._rename_by_regex(new_filename, reg, repl)
            elif idx == 0:
                LOGGER.error("No regex defined in fileregex1 settings !")

        # update record with new filename
        with Database.get_app().app_context():
            records = Diffusion.query.filter_by(original_file=self.original_filename).all()
        self.update_database(records, "final_file", new_filename)
        self.new_filename = new_filename

    def compile_archive(self):
        instr_file_path = self._create_diffmet_instr()

        basename = os.path.basename(instr_file_path)
        basename = basename.replace(".diffusions.xml", ".tar.gz")
        archive_path = os.path.join(self.dir_c, basename)

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(instr_file_path, arcname=os.path.basename(instr_file_path))
            LOGGER.debug("Compressed diffmet instruction file %s in %s.",
                        instr_file_path, archive_path)
            tar.add(self.new_file_path, arcname=os.path.basename(self.new_file_path))
            LOGGER.debug("Compressed dissemination file %s in %s.",
                        self.new_file_path, archive_path)

        LOGGER.debug("Removing processed instruction file %s", instr_file_path)
        os.remove(instr_file_path)
        LOGGER.debug("Removing processed data file %s", self.new_file_path)
        os.remove(self.new_file_path)
        with Database.get_app().app_context():
            records = Diffusion.query.filter_by(final_file=self.new_filename).all()
        self.update_database(records, "rxnotif", False)

    def update_database(self, records, key, value):

        # fetch database
        database = Database.get_database()
        for rec in records:
            setattr(rec, key, value)

        with Database.get_app().app_context():
            database.session.commit()

    def _get_priority(self):

        #TODO mettre en valeur constante
        priority_list = []
        for req_id in self.instructions.keys():
            priority = self._get_instr(req_id, "diffpriority")
            priority_list.append(priority)

        highest_priority = min(priority_list + [PRIORITIES.default])

        return highest_priority

    def _get_end_date(self):

        limit = SettingsManager.get("fileEndLive") or 0

        end_date = datetime.utcnow() + timedelta(seconds=limit*60)

        end_date = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        return end_date

    def _get_file_size(self):

        new_path = os.path.join(self.dir_b, self.new_filename)

        return os.stat(new_path).st_size


    def _get_port_value(self, diff_attributes):

        port = diff_attributes["port"]
        encrypted = diff_attributes["encrypted"]
        if port in [None,""]:
            if encrypted:
                res = "sftp"
            else:
                res = "ftp"
        elif port == "21":
            res = "ftp"
        elif port == "22":
            res = "sftp"
        elif encrypted:
            res = "sftp:" + port
        else:
            res = "ftp:" + port

        return res


    def _create_diffmet_instr(self):

        def binBool(in_boolean):
            return str(int(in_boolean))

        def diffInfoToXml(element,diff_info,prefix=""):
            if diff_info["DiffusionType"] == "FTP":
                etree.SubElement(element, prefix + "media").text="FTP"
                etree.SubElement(element, prefix + "ftp_host").text = str(diff_info["host"])
                etree.SubElement(element, prefix + "ftp_user").text = str(diff_info["user"])
                etree.SubElement(element, prefix + "ftp_passwd").text = str(diff_info["password"])
                etree.SubElement(element, prefix + "ftp_directory").text = str(diff_info["remotePath"])
                etree.SubElement(element, prefix + "ftp_use_size").text = binBool(diff_info["checkFileSize"])
                etree.SubElement(element, prefix + "ftp_passive").text = binBool(diff_info["passive"])
                etree.SubElement(element, prefix + "ftp_port").text = self._get_port_value(diff_info)
                etree.SubElement(element, prefix + "ftp_final_file_name").text = str(diff_info["fileName"])


            elif diff_info["DiffusionType"] == "EMAIL":
                etree.SubElement(element, prefix + "media").text = "EMAIL"
                etree.SubElement(element, prefix + "email_adress").text = str(diff_info["address"])
                #TODO check correspondance for BCC value
                etree.SubElement(element, prefix + "email_to_cc").text = str(diff_info["dispatchMode"])
                etree.SubElement(element, prefix + "email_subject").text = str(diff_info["subject"])
                etree.SubElement(element, prefix + "email_text_in_body").text = "0"
                # etree.SubElement(element, prefix + "email_preamble").text = ""
                if diff_info["fileName"] == "":
                    etree.SubElement(element, prefix + "email_attached_file_name").text = str(diff_info["fileName"])
                else:
                    etree.SubElement(element, prefix + "email_attached_file_name").text = DEFAULT_ATTACHMENT_NAME

        date_str = strftime("%Y%m%d%H%M%S")
        path_to_file = ",".join((SettingsManager.get("diffFileName"),
                                 self.incr,
                                 "",
                                 date_str,
                                 ))
        path_to_file += ".diffusions.xml"
        path_to_file = os.path.join(self.dir_b, path_to_file)

        root = etree.Element("product_diffusion")
        product = etree.SubElement(root, "product")
        etree.SubElement(product,"file_name").text = self.new_filename
        etree.SubElement(product,"file_size").text = str(self._get_file_size())
        etree.SubElement(product,"priority").text=str(self._get_priority())
        etree.SubElement(product,"archive").text="0"
        etree.SubElement(product,"end_to_live_date").text=self._get_end_date()

        for req_id in self.id_list:
            diffusion = etree.SubElement(product,"diffusion")
            instr = self.instructions[req_id]
            diff = instr["diffusion"]
            etree.SubElement(diffusion,"diffusion_externalid").text = Database.get_external_id(req_id)
            etree.SubElement(diffusion,"archive").text = "0"

            diffInfoToXml(diffusion, diff)

            if "alternativeDiffusion" in instr.keys():
                altdiff = instr["alternativeDiffusion"]
                diffInfoToXml(diffusion,altdiff)
                etree.SubElement(diffusion,"standby_media").text = altdiff["DiffusionType"]

            etree.SubElement(diffusion,"switch_method_medias_ftp").text = "NTRY"
            etree.SubElement(diffusion,"standby_switch_try_number").text = "3"

        etree.SubElement(product, "diffusionnumber").text=str(len(self.id_list))

        etree.SubElement(root, "productnumber").text="1"
        etree.ElementTree(root).write(path_to_file,
                                      pretty_print=True,
                                      encoding='UTF-8',
                                      xml_declaration=True)
        return path_to_file


if DEBUG and __name__ == '__main__':

    parser = argparse.ArgumentParser(description='File Manager process loop.')

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
    LOGGER = logging.getLogger("file_manager.manager")
    # TODO "Logging configuration set up" what does that even mean ?
    LOGGER.debug("Logging configuration set up in %s", "file_manager.manager")

    LOGGER.info("File Manager setup complete")
    FileManager.process(max_loops)