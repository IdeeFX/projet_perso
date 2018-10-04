from collections import namedtuple

DEFAULT_SETTINGS_PATH = "settings_harnais.yaml"

ReqStatus = namedtuple("REQ_STATUS", ["succeeded", "ongoing", "failed"])

REQ_STATUS = ReqStatus(succeeded="DISSEMINATED",
                       ongoing="ONGOING_DISSEMINATION",
                       failed="FAILED"
                      )

PORT = 8080

DEBUG_TIMEOUT = 30
TIMEOUT = 3600

Directories = namedtuple("REPERTORY_TREE", ["temp_dissrequest_a",
                                            "temp_dissrequest_b",
                                            "temp_dissrequest_c",
                                            "temp_dissrequest_d"
                                            ]
                        )

REPERTORY_TREE = Directories(temp_dissrequest_a="cache/A_dissreq",
                             temp_dissrequest_b="cache/B_Fromstaging",
                             temp_dissrequest_c="cache/C_tosend",
                             temp_dissrequest_d="cache/D_sending")


SftpSettings = namedtuple("SFTP_PARAMETERS", ["timeout_buffer",
                                            "workers"]
                           )

#TODO move to parameters
SFTP_PARAMETERS = SftpSettings(timeout_buffer=10,
                             workers=1)

RANDOM_ID_LENGTH = 20

PrioritiesScale = namedtuple("PRIORITIES",["maximum",
                            "minimum",
                            "default"])

PRIORITIES = PrioritiesScale(maximum=81,
                             minimum=89,
                             default=85)

default_settings = namedtuple("DEFAULT_SETTINGS", ["diffFileName",
                                                   "sendFTPlimitConn",
                                                   "delAck",
                                                   "fileEndLive"])

# fileEndLive is one week by default 7*60*24 min
# delAck is one one week by default 7 *24 h
DEFAULT_SETTINGS = default_settings(diffFileName="fr-meteo-harnaisdiss",
                                    sendFTPlimitConn=1,
                                    delAck = 7*24,
                                    fileEndLive=10080)


# TODO check if it should be a parameter
DEFAULT_ATTACHMENT_NAME = "MeteoFrance_product"

MAX_REGEX = 20

env = namedtuple("ENV", ["debug",
                         "settings",
                         "log_settings",
                         "trash",
                         "port",
                         "soap_url"])

ENV = env(debug = "MFSERV_HARNESS_DEBUG",
          settings = "MFSERV_HARNESS_SETTINGS",
          log_settings = "MFSERV_HARNESS_LOG_SETTINGS",
          trash = "MFSERV_HARNESS_TRASH",
          port = "MFSERV_NGINX_PORT",
          soap_url = "MFSERV_HARNESS_SOAP_ADRESS")