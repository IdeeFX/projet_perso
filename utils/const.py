from collections import namedtuple

DEFAULT_SETTINGS_PATH = "settings_harnais.yaml"

ReqStatus = namedtuple("REQ_STATUS", ["succeeded", "ongoing", "failed"])

REQ_STATUS = ReqStatus(succeeded="DISSEMINATED",
                       ongoing="ONGOING_DISSEMINATION",
                       failed="FAILED"
                      )

PORT = 8080

DEBUG_TIMEOUT = 10

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


ScpSettings = namedtuple("SCP_PARAMETERS", ["timeout_buffer",
                                            "workers"]
                           )

#TODO move to parameters
SCP_PARAMETERS = ScpSettings(timeout_buffer=10,
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
                                                   "fileEndLive"])

# fileEndLive is one week by default 7*3600*24 s
DEFAULT_SETTINGS = default_settings(diffFileName="fr-meteo-harnaisdiss",
                                    sendFTPlimitConn=1,
                                    fileEndLive=6.048e+5)

# should be in timedelta kwargs format
# https://docs.python.org/release/3.5.2/library/datetime.html?highlight=timedelta#datetime.timedelta
REFRESH_DATABASE_LIMIT = dict(days=5)

# TODO check if it should be a parameter
DEFAULT_ATTACHMENT_NAME = "meteo_france_product"

MAX_REGEX = 20