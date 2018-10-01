import os
from os.path import join
import logging.config
import yaml
from tempfile import gettempdir
from distutils.util import strtobool
from settings.settings_manager import SettingsManager

DEFAULT_PATH = '../settings/logging.yaml'

try:
    DEBUG = bool(strtobool(os.environ.get("MFSERV_HARNESS_DEBUG") or "False"))
except ValueError:
    DEBUG = False

def setup_logging(default_path=DEFAULT_PATH):
    """Setup logging configuration

    """

    # TODO introduce an environment variable settings

    def change_log_dir(in_dict, log_dir):
        for key in in_dict["handlers"].keys():
            try:
                original_path = in_dict["handlers"][key]["filename"]
            except KeyError:
                continue
            new_path = join(log_dir, os.path.basename(original_path))
            in_dict["handlers"][key]["filename"] = new_path

    setup_dir = os.path.dirname(__file__)
    default_path = join(setup_dir, default_path)
    path = os.path.abspath(default_path)
    if os.path.exists(path):
        with open(path, 'rt') as file_:
            config = yaml.safe_load(file_.read())
        # use harnaislogdir settings if it has been set.
        if DEBUG:
            log_dir = join(gettempdir(), "harnais")
            dir_error_msg = ("Incorrect logdir value {v}. "
                            "It should be the path to a valid "
                            "directory.".format(v=log_dir))
            try:
                os.mkdir(log_dir)
            except (FileExistsError,PermissionError):
                pass
        else:
            log_dir = SettingsManager.get("harnaisLogdir")
            dir_error_msg = ("Incorrect logdir value {v} in settings_harnais.yaml. "
                            "It should be the path to a valid "
                            "directory.".format(v=log_dir))
        if log_dir is not None:
            if os.path.isdir(log_dir):
                change_log_dir(config, log_dir)
            else:
                raise NotADirectoryError(dir_error_msg)
        elif SettingsManager.is_loaded():
            logging.warning("Logdir filed in settings_harnais.yaml has not been set.\n"
                            "Log files repertories will be those defined in the %s file",
                            default_path)
        else:
            error_msg = "Attempting to setup logs before the SettingsManager has been loaded"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
        logging.config.dictConfig(config)
    else:
        raise FileNotFoundError("Couldn't resolve logging configuration "
                                "file path {f}".format(f=path))

