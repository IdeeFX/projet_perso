"""
This module is responsible for creating the json file from a SOAP request
from the webservice. It also creates the initial database record corresponding
to the received requestId. 
"""
import logging
import json
import socket
from socket import herror, gaierror
import os
from time import gmtime, strftime
from datetime import datetime
from settings.settings_manager import SettingsManager
from distutils.util import strtobool
from utils.setup_tree import HarnessTree
from utils.database import Database, Diffusion
from utils.const import REQ_STATUS, PRIORITIES
from utils.tools import Tools
from utils.log_setup import setup_logging
from utils.setup_tree import HarnessTree



LOGGER = logging.getLogger(__name__)


class Notification():

    def __init__(self, req_id, uri, diss_info, client_ip):

        self.req_id = req_id
        self.uri = uri
        self.diss_info = diss_info
        self.date_reception = gmtime()
        self.request_file = ""
        self._diff_externalid = None
        self.hostname = self.get_hostname(client_ip)
        #load settings, if it has not been done
        if not SettingsManager.is_loaded():
            SettingsManager.load_settings()
            # initialize LOGGER
            setup_logging()
            # setup repertory structure
            HarnessTree.setup_tree()

        # Setting up database if necessary
        if Database.get_database() is None:
            from webservice.server.application import APP
            Database.initialize_database(APP)
            LOGGER.debug("Database setup")


        LOGGER.debug("Created a Notification object with id %s", req_id)

    @staticmethod
    def compute_priority(priority, sla):

        # priority is scaled from 1 (highest) to 4 (lowest)
        # sla is 0 (BRONZE), 1 (SILVER), 2 (GOLD)

        priority_activated = SettingsManager.get("sla")

        if type(priority_activated) == str:
            priority_activated = strtobool(priority_activated)

        if priority_activated == False:
            result = SettingsManager.get("defaultPriority") or PRIORITIES.default
        elif priority ==1:
            result = PRIORITIES.maximum
        elif priority >=2:
            default_priority = SettingsManager.get("defaultPriority") or PRIORITIES.default
            result = default_priority + priority - 2*sla
            result = max(PRIORITIES.maximum, result)
            result = min(PRIORITIES.minimum, result)

        return result


    def create_request_file(self):

        #compute priority
        priority = self.compute_priority(self.diss_info.priority,
                                         self.diss_info.SLA)

        out_dir = HarnessTree.get("temp_dissRequest_A")

        rec_dict = dict(hostname=self.hostname)
        rec_dict["priority"] = priority
        rec_dict["date_reception"] = strftime(
            "%Y%m%d%H%M%S", self.date_reception)
        rec_dict["requestid"] = self.req_id

        request_file = "{priority}_{date_reception}_{requestid}_{hostname}.json".format(
            **rec_dict)

        self.request_file = request_file = os.path.join(out_dir, request_file)

        request_dump = dict(date=rec_dict["date_reception"],
                            hostname=self.hostname,
                            diffpriority=priority,
                            uri=self.uri,
                            req_id = self.req_id
                            )

        request_diff = self.compile_request()
        request_dump.update(request_diff)

        LOGGER.debug("Attempting to write {file}".format(file=request_file))
        with open(request_file, "w") as file_:
            json.dump(request_dump, file_, indent=4)
        LOGGER.info("Successfully wrote instruction file %s ", request_file)

    def compile_request(self):

        def dump_attributes(obj):
            from webservice.server.soapInterface import FTPDiffusion, MailDiffusion
            attr_dump = dict()
            if isinstance(obj, FTPDiffusion):
                attr_dump["DiffusionType"] = "FTP"
            elif isinstance(obj, MailDiffusion):
                attr_dump["DiffusionType"] = "EMAIL"
            for key in obj.__dict__.keys():
                if key[0] != "_" and key != "Attributes":
                    value = getattr(obj, key)
                    attr_dump[key] = value
            return attr_dump

        diff = self.diss_info.diffusion
        alt_diff = self.diss_info.alternativeDiffusion
        request = dict()
        request["diffusion"] = dump_attributes(diff)
        if alt_diff is not None:
            request["alternativeDiffusion"] = dump_attributes(alt_diff)

        return request

    @staticmethod
    def _to_datetime(struct_time_date):

        return  datetime(struct_time_date.tm_year,
                         struct_time_date.tm_mon,
                         struct_time_date.tm_mday,
                         struct_time_date.tm_hour,
                         struct_time_date.tm_min,
                         struct_time_date.tm_sec)

    def process(self):

        self._diff_externalid = diff_id = Tools.generate_random_string()

        # fetch database
        database = Database.get_database()

        try:
            # create JSON request file
            self.create_request_file()

            diffusion = Diffusion(diff_externalid=diff_id,
                                  fullrequestId=self.req_id+self.hostname,
                                  requestStatus=REQ_STATUS.ongoing,
                                  Date=self._to_datetime(self.date_reception),
                                  rxnotif=True,
                                  message="Created record in SQL database",)
            with Database.get_app().app_context():
                database.session.add(diffusion)
                database.session.commit()
            LOGGER.debug("Committed %s dissemination status "
                         "into database.", REQ_STATUS.ongoing)
            status = REQ_STATUS.ongoing
        except Exception as exc:
            LOGGER.exception("Error during notification processing. "
                             "Dissemination failed.")
            status = self.commit_failure(database, diff_id)
        return status

    def commit_failure(self, database, diff_id):

        diffusion = Diffusion(diff_externalid=diff_id,
                              fullrequestId=self.req_id,
                              requestStatus=REQ_STATUS.failed,
                              Date=self._to_datetime(self.date_reception),
                              rxnotif=True)

        with Database.get_app().app_context():
            database.session.add(diffusion)
            database.session.commit()

        LOGGER.info("Committed %s dissemination status into database.",
                    REQ_STATUS.failed)

        if os.path.isfile(self.request_file):
            Tools.remove_file(self.request_file, "JSON request", LOGGER)

        return REQ_STATUS.failed

    @staticmethod
    def get_hostname(client_ip):
        # get hostname
        try:
            hostname = socket.gethostbyaddr(client_ip)[0]
            hostname = hostname.replace(".","-")
            LOGGER.debug("Got hostname {host} for {ip}".format(
                host=hostname, ip=client_ip))
        except (herror, gaierror):
            LOGGER.exception("Couldn't get hostname from ip %s, "
                             "using ip as hostname instead.", client_ip)
            hostname = client_ip
            hostname = hostname.replace(".","-")

        return hostname


