import yaml
import os
import logging
from multiprocessing.pool import Pool
from multiprocessing.dummy import Pool as ThreadPool
from utils.const import DEFAULT_SETTINGS_PATH, DEFAULT_SETTINGS, ENV, MAX_REGEX
from utils.tools import Tools

LOGGER = logging.getLogger(__name__)


def compact_dict(in_dict, prefix="", exceptions=[]):

    out_dict = dict()

    for k, val in in_dict.items():

        if isinstance(val, dict) and k.lower() not in exceptions:
            child_dict = compact_dict(val, prefix=k)
            out_dict.update(child_dict)
        else:
            out_dict[prefix + k] = val

    return out_dict


class SettingsManager:

    _parameters = dict(harnaisLogdir=None,
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
                       dissFtpMode=None,
                       dissFtpPort=None,
                       soapPort=None,
                       processFileIdle=None,
                       processFileDPmax=None,
                       processFilesize=None,
                       keepFileTime=None,
                       bandwidth=None,
                       tmpregex=None,
                       sla=None,
                       delAck=DEFAULT_SETTINGS.delAck,
                       delfaultPriority=None,
                       diffFileName=DEFAULT_SETTINGS.diffFileName,
                       fileEndLive=DEFAULT_SETTINGS.fileEndLive,
                       sendFTPIdle=None,
                       sendFTPlimitConn=DEFAULT_SETTINGS.sendFTPlimitConn)
    _loaded = False
    _checksum = None
    _settings_file = None

    @classmethod
    def load_settings(cls, settings_file=DEFAULT_SETTINGS_PATH, reloading=False):
        loaded = False

        #TODO document use of config.ini /etc/metwork.config.d/mfserv/config.ini to set
        # an environnement variable

        # load yaml settings file
        #TODO move MFSERV_HARNAIS_SETTINGS into const
        path = cls._settings_file = os.environ.get(ENV.settings, None)
        if path is None:
            path = cls._settings_file = os.path.join(os.path.dirname(__file__), settings_file)

        # TODO check if file can be opened

        checksum = Tools.checksum_file(path)

        if reloading or checksum != cls._checksum:
            for i in range(1, MAX_REGEX+1):
                cls._parameters["fileRegex%i" % i] = dict()

            with open(path, "r") as file_:
                settings = yaml.safe_load(file_)

            # TODO implement value check
            # TODO check if interger for port value
            # TODO check if diffFileName has been defined

            # TODO should be better than this hack
            exceptions = ["fileregex%i" %i for i in range(1,MAX_REGEX+1)]
            settings = compact_dict(settings, exceptions=exceptions)

            # set up with class variables
            for key in cls._parameters.keys():
                for set_key, value in settings.items():
                    if set_key.lower() == key.lower() and value is not None:
                        cls._parameters[key] = value


            cls._loaded = loaded = True
            cls._checksum = checksum


        return loaded

    @classmethod
    def is_loaded(cls):
        return cls._loaded


    @classmethod
    def reload(cls):
        # TODO
        cls.reset()
        cls.load_settings(reloading=True)

    @classmethod
    def reset(cls):

        for key in cls._parameters.keys():
            cls._parameters[key] = None
        cls._loaded = False

    @classmethod
    def get(cls, key, alt=None):

        if not cls._loaded:
            raise RuntimeError("Attempting to access SettingsManager "
                               "before it has been loaded.")
        checksum = Tools.checksum_file(cls._settings_file)

        if checksum != cls._checksum:
            cls.load_settings()

        return cls._parameters.get(key,alt)

    @classmethod
    def get_checksum(cls):

        if cls._checksum is None:
            raise RuntimeError("Attempting to get checksum before it had been calculated.")

        return cls._checksum

    @classmethod
    def setter(cls, key, value, testing=False):

        if not testing:
            LOGGER.warning("SettingsManager class attributes are NOT"
                           " meant to be set outside of tests.")
        cls._parameters[key] = value

    @classmethod
    def update(cls, in_dict, testing=False):
        if not testing:
            LOGGER.warning("SettingsManager class attributes are NOT"
                           " meant to be set outside of tests.")
        cls._parameters.update(in_dict)

class DebugSettingsManager:

    sftp_pool = ThreadPool
    ftp_pool = ThreadPool
