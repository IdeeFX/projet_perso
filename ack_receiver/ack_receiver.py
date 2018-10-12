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
from settings.settings_manager import SettingsManager
from webservice.server.application import APP




# initialize LOGGER
LOGGER = logging.getLogger(__name__)
LOGGER_ACK = logging.getLogger("difmet_ack_messages")
LOGGER_ALARM =   logging.getLogger("difmet_alarm_messages")
LOGGER.debug("Logging configuration set up for %s", __name__)
# TODO move environment variables into utils.const
try:
    DEBUG = bool(strtobool(os.environ.get(ENV.debug) or "False"))
except ValueError:
    DEBUG = False

class AckReceiver:

    _running = False
    dir_ack = None


    @classmethod
    def process(cls, max_loops=0):
        counter = 0
        cls.setup_process()
        while cls._running:
            counter += 1
            cls.signal_loop(counter)
            cls.load_settings()
            # TODO check default value
            idle_time = SettingsManager.get("sendFTPIdle") or 10
            sleep(idle_time)
            cls.dir_ack = dir_ack = HarnessTree.get("dir_ack")

            cls.process_ack_files(dir_ack)
            cls.process_alarm_files(dir_ack)

            if counter == max_loops:
                LOGGER.info("Performed required %i loops, exiting.", counter)
                cls.stop()

    @classmethod
    def setup_process(cls):
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
        for file_ in listdir(dir_ack):
            file_path = join(dir_ack, file_)
            ack_file = re.match(r".*.acqdifmet.xml$", file_)
            if ack_file is None:
                continue
            LOGGER.debug("Processing difmet ack file %s.", file_)
            cls.get_ack(file_path)
            Tools.remove_file(file_path, "difmet ack", LOGGER)

    @classmethod
    def process_alarm_files(cls, dir_ack):
        for file_ in listdir(dir_ack):
            file_path = join(dir_ack, file_)
            alarme_file = re.match(r".*.errdifmet.xml$", file_)
            if alarme_file is None:
                continue
            LOGGER.debug("Processing difmet alarm file %s.", file_)
            cls.get_alarm(file_path)
            Tools.remove_file(file_path, "difmet alarm", LOGGER)

    @classmethod
    def stop(cls):
        LOGGER.info("Received request for %s process to stop looping.",
                     cls.__name__)
        cls._running = False

    @staticmethod
    def _check_file_age(filename):
        time_limit = SettingsManager.get("delAck")
        return (time() - os.stat(filename).st_mtime) > time_limit

    @classmethod
    def get_alarm(cls, file_):
        req_id = None

        tree = etree.parse(file_)
        root = tree.getroot()

        for alarm in root.findall("alarm"):
            diff_external_id = alarm.findtext("diffusion_externalid")

            keys = ["date",
                    "severity",
                    "error",
                    "error_text"
                    "subscriber_name"]

            msg_list = ["diffusion_externalid = %s" % diff_external_id]

            for key in keys:
                val = alarm.findtext(key)
                msg_list.append('{k} : {v}'.format(k=key,v=val))

            alarm_msg = msg_list[0] + "\n".join(msg_list)
            LOGGER_ALARM.debug("Alarm message is : \n %s", alarm_msg)

        for handler in LOGGER_ALARM.handlers:
            LOGGER.info("Logged an alarm message into "
                        "log file %s", handler.baseFilename)
        if req_id is not None:
            cls.update_database_status(alarm_msg)


    @classmethod
    def get_ack(cls, file_):
        diff_success = False
        tree = etree.parse(file_)
        root = tree.getroot()
        req_id = None

        for ack in root.findall("acquittement"):
            #TODO que signifie "quand il est présent" ?
            # TODO check if it should be the fullrequestId or diff_externalid
            diff_external_id = ack.findtext("diffusion_externalid")
            dtb_key = dict(diff_externalid=diff_external_id)
            prod_id = ack.findtext("productid")
            req_id = Database.get_id_by_query(**dtb_key)
            status = ack.findtext("status")
            ack_type = ack.findtext("type")
            # channel =

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

            if ack_type == "SEND" and status == "OK":
                diff_success = True
                cls.update_database_status(diff_success, req_id)
                msg = ("DiffMet ack reports success for product %s "
                       "corresponding to request %s" %
                       (prod_id,
                       req_id))
                LOGGER.info(msg)
                cls.update_database_message(msg, req_id)
            else:
                ack_type_failure = ack_type
                status_failure = status
            # Log the full ack
            msg_list = ["fullrequestId = %s" % req_id,
                        "diffusion_externalid = %s" % diff_external_id,
                        ]
            for key in keys:
                val = ack.findtext(key)
                msg_list.append('{k} : {v}'.format(k=key,v=val))
            ack_msg = "\n".join(msg_list)
            LOGGER_ACK.debug("Ack message is : \n%s", ack_msg)

        if not diff_success:
            cls.update_database_status(diff_success, req_id)
            msg = ("DiffMet ack reports error for product %s "
                   "corresponding to request %s with status %s "
                   "for request of type %s." %
                   (prod_id,
                   req_id,
                   ack_type_failure,
                   status_failure))
            LOGGER.error(msg)
            cls.update_database_message(msg, req_id)

        for handler in LOGGER_ACK.handlers:
            LOGGER.info("Logged an ack message into "
                        "log file %s", handler.baseFilename)

        if diff_success and req_id is None:
            LOGGER.error("Couldn't retrieve dissemination requestId "
                         "from external_id %s", diff_external_id)


    @classmethod
    def update_database_status(cls, diff_success, diff_id):

        if not diff_success:
            msg = ("Diffmet reported that diffusion %s failed.", diff_id)
            LOGGER.info(msg)
            Database.update_field_by_query("requestStatus", REQ_STATUS.failed,
                                            **dict(fullrequestId=diff_id))
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
    def update_database_message(cls, message, diff_id):

        Database.update_field_by_query("message", message,
                                        **dict(fullrequestId=diff_id))

if __name__ == '__main__':
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
    setup_logging()
    LOGGER = logging.getLogger("ack_receiver.ack_receiver")
    LOGGER.debug("Logging configuration set up for %s", "ack_receiver.ack_receiver")

    LOGGER.info("File Manager setup complete")
    AckReceiver.process(max_loops)