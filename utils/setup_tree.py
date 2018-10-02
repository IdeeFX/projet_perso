import os
from os.path import join
import logging
import tempfile
from distutils.util import strtobool
from settings.settings_manager import SettingsManager
from utils.const import REPERTORY_TREE

try:
    DEBUG = bool(strtobool(os.environ.get("MFSERV_HARNESS_DEBUG") or "False"))
except ValueError:
    DEBUG = False

# initialize LOGGER
LOGGER = logging.getLogger(__name__)


SettingsManager.load_settings()
LOGGER.debug("Settings loaded")

class HarnessTree:

    _repertories = dict(temp_dissRequest_A=None,
                        temp_dissRequest_B=None,
                        temp_dissRequest_C=None,
                        temp_dissRequest_D=None,
                        dir_ack=None)
    _checksum = None

    @classmethod
    def setup_tree(cls, update=False):

        if update:
            LOGGER.info("Settings modified, performing a check on the "
                        "repertories tree structure, updating it if necessary")

        if not SettingsManager.is_loaded():
            error_msg = ("Attempting to setup repertories "
                         "tree structure before the SettingsManager "
                         "has been loaded")
            LOGGER.error(error_msg)
            raise RuntimeError(error_msg)

        def setup_repertory(dir_path):

            if not os.path.isdir(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    LOGGER.debug(
                        "Repertory {rep} created recursively.".format(rep=dir_path))
                #TODO clean that up
                except Exception as msg_error:
                    LOGGER.exception(
                        "Couldn't create repertory {rep}.".format(rep=dir_path))
            return dir_path

        if DEBUG:
            harnais_dir = os.path.join(tempfile.gettempdir(), "harnais")
        else:
            harnais_dir = SettingsManager.get("harnaisDir")
        # repertory of temporary dissRequest JSON files
        cls._repertories["temp_dissRequest_A"] = setup_repertory(
            join(harnais_dir,
                 REPERTORY_TREE.temp_dissrequest_a)
                                                                )
        cls._repertories["temp_dissRequest_B"] = setup_repertory(
            join(harnais_dir,
                 REPERTORY_TREE.temp_dissrequest_b)
                                                                )
        cls._repertories["temp_dissRequest_C"] = setup_repertory(
            join(harnais_dir,
                 REPERTORY_TREE.temp_dissrequest_c)
                                                                )
        cls._repertories["temp_dissRequest_D"] = setup_repertory(
            join(harnais_dir,
                 REPERTORY_TREE.temp_dissrequest_d)
                                                                )

        cls._repertories["dir_ack"] = dir_ack = SettingsManager.get("harnaisAckDir")

        if not os.path.isdir(cls._repertories["dir_ack"]):
            LOGGER.error("Ack repertory %s does "
                         "not exist", dir_ack)
            # TODO raise

        # storing the settings file signature
        cls._checksum = SettingsManager.get_checksum()


    @classmethod
    def get(cls, key):
        #check if settings have been modified
        if SettingsManager.get_checksum() != cls._checksum:
            LOGGER.info("Settings have been modified")
            cls.setup_tree(update=True)
        return cls._repertories[key]

    @classmethod
    def setter(cls, key, value, testing=False):
        if not testing:
            LOGGER.warning("HarnessTree class attributes are NOT"
                           " meant to be set outside of tests.")
        cls._repertories[key] = value

    @classmethod
    def update(cls, in_dict, testing=False):
        if not testing:
            LOGGER.warning("HarnessTree class attributes are NOT"
                           " meant to be set outside of tests.")
        cls._repertories.update(in_dict)
