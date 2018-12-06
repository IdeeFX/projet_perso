"""
    This module processes the ack files sent by difmet and update
    the database status for the corresponding request Id to 
    failure, success or keep it at ongoing.
"""
import logging
import os
from os import listdir
from os.path import join
import re
import argparse
from time import time, sleep
from lxml import etree
from distutils.util import strtobool
from setproctitle import setproctitle
from utils.setup_tree import HarnessTree
from utils.const import REQ_STATUS, ENV
from utils.log_setup import setup_logging
from utils.tools import Tools
from utils.database import Database, Diffusion
from settings.settings_manager import SettingsManager, DebugSettingsManager
from webservice.server.application import APP




# initialize LOGGER
LOGGER = logging.getLogger(__name__)
LOGGER_ACK = logging.getLogger("difmet_ack_messages")
LOGGER_ALARM =   logging.getLogger("difmet_alarm_messages")
LOGGER.debug("Logging configuration set up for %s", __name__)
try:
    DEBUG = strtobool(os.environ.get(ENV.debug) or DebugSettingsManager.get("debug"))
except ValueError:
    DEBUG = False

class AckReceiver:
    """
    This class processes the ack files sent by difmet and update
    the database status for the corresponding request Id to 
    failure, success or keep it at ongoing.
    """

    #Variables to store the ack deposit repertory and the status of the process
    _running = False
    dir_ack = None


    @classmethod
    def process(cls, max_loops=0):
        counter = 0
        cls.setup_process()
        while cls._running:
            counter += 1
            cls.signal_loop(counter)
            # load settings
            cls.load_settings()
            idle_time = SettingsManager.get("ackProcessIdle")
            sleep(idle_time)
            cls.dir_ack = dir_ack = HarnessTree.get("dir_ack")

            # process ack files
            cls.process_ack_files(dir_ack)
            # process alarm files
            cls.process_alarm_files(dir_ack)

            # for testing and debugging purpose only
            if counter == max_loops:
                LOGGER.info("Performed required %i loops, exiting.", counter)
                cls.stop()

    @classmethod
    def setup_process(cls):
        """
        Prepare logging, check the repertories and connect to database
        """
        if not cls._running:
            setup_logging()
            LOGGER = logging.getLogger(__name__)
            LOGGER.info("Ack receiver process starting")
            # create tree structure if necessary
            HarnessTree.setup_tree()
            #connect the database
            Database.initialize_database(APP)
            cls._running = True

    @staticmethod
    def signal_loop(counter):
        if counter % 10 ==0:
            LOGGER.debug("Ack receiver is running. "
                         "Loop number %i", counter)
            if DEBUG:
                LOGGER.warning("DEBUG mode activated.")

    @staticmethod
    def load_settings():
        loaded = SettingsManager.load_settings()
        if loaded:
            LOGGER.debug("Settings loaded")

    @staticmethod
    def check_ack_dir(dir_ack):
        if not os.path.isdir(dir_ack):
            LOGGER.error("Ack dir %s is not a repertory %s", dir_ack)
            raise NotADirectoryError


    @classmethod
    def process_ack_files(cls, dir_ack):
        """
        Loop on files on dir_ack to find ack files.
        If found, it is processed
        """
        for file_ in listdir(dir_ack):
            file_path = join(dir_ack, file_)
            ack_file = re.match(r".*.acqdifmet.xml$", file_)
            if ack_file is None:
                continue
            LOGGER.debug("Processing difmet ack file %s.", file_)
            # interpreting the ack file
            cls.get_ack(file_path)
            # removing the file now that it has been read
            Tools.remove_file(file_path, "difmet ack", LOGGER)

    @classmethod
    def process_alarm_files(cls, dir_ack):
        """
        Loop on files on dir_ack to find alarm files.
        If found, it is processed
        """
        for file_ in listdir(dir_ack):
            file_path = join(dir_ack, file_)
            alarme_file = re.match(r".*.errdifmet.xml$", file_)
            if alarme_file is None:
                continue
            LOGGER.debug("Processing difmet alarm file %s.", file_)
            # interpreting the alarm file
            cls.get_alarm(file_path)
            # removing the file now that it has been read
            Tools.remove_file(file_path, "difmet alarm", LOGGER)

    @classmethod
    def stop(cls):
        """
        Stop the process
        """
        LOGGER.info("Received request for %s process to stop looping.",
                     cls.__name__)
        cls._running = False

    @staticmethod
    def _check_file_age(filename):
        """
        Discard files that are too old
        """
        time_limit = SettingsManager.get("delAck")
        return (time() - os.stat(filename).st_mtime) > time_limit

    @classmethod
    def get_alarm(cls, file_):
        """
        Process an alarm file
        """


        tree = etree.parse(file_)
        root = tree.getroot()

        # loop on all the alarm groups in the file and log the messages
        for alarm in root.findall("alarm"):
            diff_external_id = alarm.findtext("diffusion_externalid")
            dtb_key = dict(diff_externalid=diff_external_id)
            req_id = Database.get_id_by_query(**dtb_key)
            keys = ["date",
                    "severity",
                    "error",
                    "error_text",
                    "subscriber_name"]

            msg_list = ["diffusion_externalid = %s" % diff_external_id]

            for key in keys:
                val = Tools.ack_decode(alarm.findtext(key))
                msg_list.append('{k} : {v}'.format(k=key,v=val))

            alarm_msg = "\n".join(msg_list)
            LOGGER_ALARM.debug("Alarm message is : \n %s", alarm_msg)

             # Update the database with the message if possible
            if req_id is not None:
                cls.update_database_message(alarm_msg, req_id, diff_external_id)

        for handler in LOGGER_ALARM.handlers:
            LOGGER.info("Logged an alarm message into "
                        "log file %s", handler.baseFilename)

    @classmethod
    def get_ack(cls, file_):
        tree = etree.parse(file_)
        root = tree.getroot()
        req_id = None

        # we read the ack file for finding diffusion_externalid
        # and storing them in a ack_compiler object
        ack_compiler = AckCompiler()
        for ack in root.findall("acquittement"):
            diff_external_id= ack.findtext("diffusion_externalid")
            prod_id = ack.findtext("productid")
            ack_compiler.add_ack_status(diff_external_id, prod_id)

        # now, we check their status
        for ack in root.findall("acquittement"):
            diff_external_id = ack.findtext("diffusion_externalid")
            # get corresponding status:
            ack_status = ack_compiler.get_status(diff_external_id)
            req_id = ack_status.req_id
            prod_id = ack.findtext("productid")
            status = ack.findtext("status")
            ack_type = ack.findtext("type")
            keys = ["type",
                    "status",
                    "productid",
                    "product_internalid",
                    "diffusion_internalid",
                    "channel",
                    "media",
                    "ftp_host",
                    "ftp_user",
                    "ftp_directory",
                    "email_adress"]

            ack_status.status_to_process.append((ack_type, status))

            # Log the full ack
            msg_list = ["fullrequestId = %s" % req_id,
                        "diffusion_externalid = %s" % diff_external_id,
                        ]
            for key in keys:
                val = Tools.ack_decode(ack.findtext(key))
                msg_list.append('{k} : {v}'.format(k=key,v=val))
            ack_msg = "\n".join(msg_list)
            LOGGER_ACK.debug("Ack message is : \n%s", ack_msg)

        # we compile the status and deduce the resulting REQ_STATUS to return
        for ack_status in ack_compiler.status_list:
            ext_id = ack_status.ext_id
            req_id = ack_status.req_id
            prod_id = ack_status.prod_id
            ack_type, status, final_status = ack_status.compile_status()

            if final_status == "ongoing":
                msg = "Received DifMet ack for request %s corresponding to product %s " % (req_id, prod_id)
                LOGGER.info(msg)
                cls.update_database_message(msg, req_id, ext_id)
            elif final_status == "success":
                cls.update_database_status(True, req_id)
            elif final_status == "failure":
                cls.update_database_status(False, req_id)
                msg = ("DiffMet ack reports error for product %s "
                    "corresponding to request %s with status %s "
                    "for type %s." %
                    (prod_id,
                    req_id,
                    ack_type,
                    status))
                LOGGER.error(msg)
                cls.update_database_message(msg, req_id, ext_id)



        # # case where there is only the ack corresponding to reception
        for handler in LOGGER_ACK.handlers:
            LOGGER.info("Logged an ack message into "
                        "log file %s", handler.baseFilename)


    @classmethod
    def update_database_status(cls, diff_success, diff_id):

        current_status = Database.get_request_status(diff_id)

        if not diff_success:
            if current_status != REQ_STATUS.ongoing:
                msg = ("Difmet reports failure for request %s but "
                      "current status is not %s !" % (diff_id, REQ_STATUS.ongoing))
                LOGGER.error(msg)
                Database.update_field_by_query("message", msg,
                                               **dict(fullrequestId=diff_id))
            else:
                msg = ("Diffmet reported that diffusion %s failed." % diff_id)
                LOGGER.info(msg)
                Database.update_field_by_query("requestStatus", REQ_STATUS.failed,
                                                **dict(fullrequestId=diff_id))
                Database.update_field_by_query("message", msg,
                                            **dict(fullrequestId=diff_id))
        else:
            if current_status != REQ_STATUS.ongoing:
                msg = ("Difmet reports success for request %s but "
                      "current status is not %s !" % (diff_id, REQ_STATUS.ongoing))
                LOGGER.error(msg)
                Database.update_field_by_query("message", msg,
                                               **dict(fullrequestId=diff_id))
            else:
                msg = ("Diffmet reported that diffusion %s succeeded." % diff_id)
                LOGGER.info(msg)
                Database.update_field_by_query("requestStatus", REQ_STATUS.succeeded,
                                                **dict(fullrequestId=diff_id))
                Database.update_field_by_query("message", msg,
                                            **dict(fullrequestId=diff_id))

    @classmethod
    def update_database_message(cls, message, diff_id, ext_id):

        Database.update_field_by_query("message", message,
                                        **dict(fullrequestId=diff_id,
                                               diff_externalid=ext_id)
                                      )


class AckCompiler:
    """
    This object stores all the AckStatus objects and their corresponding diff_ext_id.
    """

    def __init__(self):
        self.diff_ext_id = []
        self.status_list = []

    def add_ack_status(self, ext_id, prod_id):
        if ext_id not in self.diff_ext_id:
            self.diff_ext_id.append(ext_id)
            self.status_list.append(AckStatus(ext_id, prod_id))

    def get_status(self, ext_id):
        for i, id_stored in enumerate(self.diff_ext_id):
            if id_stored == ext_id:
                break
        ack_status = self.status_list[i]

        return ack_status



class AckStatus:

    """
    This object connects the diff_external_id to the fullrequestId 
    and compile the status once all the ack have been read in 
    the ack file.
    """

    def __init__(self, ext_id, prod_id):
        self.ext_id = ext_id
        dtb_key = dict(diff_externalid=ext_id)
        req_id = Database.get_id_by_query(**dtb_key)
        if req_id is None:
            LOGGER.error("Couldn't retrieve dissemination requestId "
                         "from external_id %s", ext_id)
            self.records_number = 0
        else:
            #we fetch the number of records that have to be checked
            self.records_number = Database.get_records_number(req_id)
        self.req_id = req_id
        self.prod_id = prod_id
        self.status_to_process = []

        

    def compile_status(self):

        final_status = "ongoing"

        counter=0
        for ack_type, status in self.status_to_process:
            if ack_type == "SEND" and status == "OK":
                final_status = "success"
            elif ack_type == "SEND" and status != "OK":
                final_status= "failure"
                break
            
        
        if final_status=="success":
            # we update the number of diffusion reported
            Database.update_field_by_query("rxnotif", True, **dict(diff_externalid=self.ext_id))
            
            #we check that all requested files have been sent
            nb_diff = Database.get_diffusion_number(self.req_id)
            if self.records_number!=nb_diff:
                final_status = "ongoing"
                LOGGER.info("ack file reports that %i diffusion have been performed on"
                            "the %i required for diffusion  %s", nb_diff, 
                            self.records_number, self.req_id)



        return ack_type, status, final_status



if __name__ == '__main__':


    # this is used for testing and debugging purpose only. It allows to launch the process independently
    # for user specified n loops
    process_name = "harness_ack_receiver"
    setproctitle(process_name)

    parser = argparse.ArgumentParser(description='Ack receiver process loop.')

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
    LOGGER = logging.getLogger("ack_receiver.ack_receiver")
    LOGGER.debug("Logging configuration set up for %s", "ack_receiver.ack_receiver")

    LOGGER.info("File Manager setup complete")
    AckReceiver.process(max_loops)
