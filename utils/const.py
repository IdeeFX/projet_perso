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

TIMEOUT_BUFFER = 1

RANDOM_ID_LENGTH = 20

MSG_MAX_LENGTH = 255

PrioritiesScale = namedtuple("PRIORITIES",["maximum",
                            "minimum",
                            "default"])

PRIORITIES = PrioritiesScale(maximum=81,
                             minimum=89,
                             default=85)

default_settings = namedtuple("DEFAULT_SETTINGS", ["harnaisLogdir",
                                                   "harnaisDir",
                                                   "harnaisAckDir",
                                                   "harnaisSynchro",
                                                   "openwisHost",
                                                   "openwisSftpUser",
                                                   "openwisSftpPassword",
                                                   "openwisSftpPort",
                                                   "openwisStagingPath",
                                                   "dissHost",
                                                   "dissFtpUser",
                                                   "dissFtpPasswd",
                                                   "dissFtpDir",
                                                   "dissFtpMode",
                                                   "dissFtpPort",
                                                   "soapPort",
                                                   "processFileIdle",
                                                   "processFileDPmax",
                                                   "getSFTPlimitConn",
                                                   "processFilesize",
                                                   "keepFileTime",
                                                   "keepFileTimeSender",
                                                   "ManagerOverflow",
                                                   "SenderOverflow",
                                                   "bandwidth",
                                                   "tmpregex",
                                                   "sla",
                                                   "delAck",
                                                   "defaultPriority",
                                                   "diffFileName",
                                                   "fileEndLive",
                                                   "sendFTPIdle",
                                                   "sendFTPlimitConn",
                                                   "ackProcessIdle",
                                                   "attachmentName"])

# fileEndLive is one week by default 7*60*24 min
# delAck is one one week by default 7 *24 h
DEFAULT_SETTINGS = default_settings(harnaisLogdir=None,
                                    harnaisDir=None,
                                    harnaisAckDir=None,
                                    harnaisSynchro=None,
                                    openwisHost=None,
                                    openwisSftpUser=None,
                                    openwisSftpPassword=None,
                                    openwisSftpPort=None,
                                    openwisStagingPath=None,
                                    dissHost=None,
                                    dissFtpUser=None,
                                    dissFtpPasswd=None,
                                    dissFtpDir=None,
                                    dissFtpMode="passive",
                                    dissFtpPort=None,
                                    soapPort=None,
                                    processFileIdle=30,
                                    processFileDPmax=10,
                                    getSFTPlimitConn = 1,
                                    processFilesize=1000,
                                    keepFileTime=14400,
                                    keepFileTimeSender=86400,
                                    ManagerOverflow = None,
                                    SenderOverflow = None,
                                    bandwidth=None,
                                    tmpregex=None,
                                    sla=False,
                                    delAck=7*24,
                                    defaultPriority=PRIORITIES.default,
                                    diffFileName="fr-meteo-harnaisdiss",
                                    fileEndLive=1440,
                                    sendFTPIdle=10,
                                    sendFTPlimitConn=1,
                                    ackProcessIdle=10,
                                    attachmentName="MeteoFrance_product")

MAX_REGEX = 20

env = namedtuple("ENV", ["debug",
                         "settings",
                         "log_settings",
                         "trash",
                         "port",
                         "soap_url",
                         "test_sftp"])

ENV = env(debug = "MFSERV_HARNESS_DEBUG",
          settings = "MFSERV_HARNESS_SETTINGS",
          log_settings = "MFSERV_HARNESS_LOG_SETTINGS",
          trash = "MFSERV_HARNESS_TRASH",
          port = "MFSERV_NGINX_PORT",
          soap_url = "MFSERV_HARNESS_SOAP_ADRESS",
          test_sftp= "MFSERV_HARNESS_TEST_SFTP")
