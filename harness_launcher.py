"""
This script is the entry point for the harness when in production. It is summoned by a crontab.
It launches and wait for an exception coming from the 3 modules (ack_receiver, manager, sender).
If one crashed, it restarts it.
"""
import logging
import os
from time import sleep
from setproctitle import setproctitle
from distutils.util import strtobool
from concurrent.futures import (ThreadPoolExecutor, ProcessPoolExecutor,
                               ALL_COMPLETED, FIRST_COMPLETED,
                               FIRST_EXCEPTION, wait)
import traceback
from file_manager.manager import FileManager
from file_sender.sender import DifmetSender
from ack_receiver.ack_receiver import AckReceiver
from utils.log_setup import setup_logging
from settings.settings_manager import SettingsManager, DebugSettingsManager
from utils.tools import Tools
from utils.const import ENV

# debug switches the launcher from a process based multiprocessing to
# a thread implementation to follow more easily the overall process
# in a debugger.
try:
    DEBUG = strtobool(os.environ.get(ENV.debug) or DebugSettingsManager.get("debug"))
except ValueError:
    DEBUG = False

LOGGER = None

def launch_named_process(proc, name):
    """
    launch a process and sets its name
    as displayed by ps -ef | grep name
    """
    if not DEBUG:
        setproctitle(name)
    proc()

def get_logger():
    """
    Fetch logger
    """
    SettingsManager.load_settings()

    # initialize LOGGER
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.debug("Logging configuration set up for %s", __name__)
    return logger

def launch(launch_logger=None, debug=True):
    """
    Launches the harness. This will launch the three modules
    - harness_difmet_sender
    - harness_file_manager
    - harness_ack_receiver

    The SOAP server is handled by MFSERV.
    """

    if launch_logger is None:
        launch_logger = get_logger()

    def log_exception(exc, proc, i):
        """
        Catch the exception messages thrown back by an exception
        """
        log_list = [("file_sender.sender", logging.getLogger("file_sender.sender")),
                    ("file_manager.manager", logging.getLogger("file_manager.manager")),
                    ("ack_receiver.ack_receiver", logging.getLogger("ack_receiver.ack_receiver"))
                ]
        log_name, logger = log_list[i]
        if exc is not None:
            launch_logger.error("Process %s was terminated. See log %s "
                    "for more information. Restarting "
                    "automatically", proc_list[i], log_name)
            # log the full traceback in the module log
            logger.error(''.join(traceback.format_exception(type(exc),
                        exc, exc.__traceback__)))


    if debug:
        executor_class = ThreadPoolExecutor
        launch_logger.info("Debug mode activated. Multiprocessing is done through threads "
                    " and not subprocess and is thus slower.")
    else:
        executor_class = ProcessPoolExecutor

    # list the process to manage
    process_status = [None]*3
    proc_list = [DifmetSender.process,
                 FileManager.process,
                 AckReceiver.process]
    proc_names = ["harness_difmet_sender",
                  "harness_file_manager",
                  "harness_ack_receiver"]

    with executor_class(max_workers=len(process_status)) as executor:
        #launch the process
        for i, proc in enumerate(proc_list):
            proc_name = proc_names[i]
            process_status[i] = executor.submit(launch_named_process, *(proc, proc_name))
            launch_logger.info("Launching %s.", proc.__qualname__)
            # sleep to avoid concurrent access to database at startup
            sleep(1)
        # 
        # Inspect the processes. If one crashes, it gets restarted.
        while True:
            sleep(10)
            for i, status in enumerate(process_status):
                proc = proc_list[i]
                if not status.running():
                    exc  = status.exception()
                    log_exception(exc, proc, i)
                    proc_name = proc_names[i]
                    process_status[i] = executor.submit(launch_named_process, *(proc, proc_name))
                    launch_logger.info("Function %s crashed, restarting.", proc.__qualname__)
                    # sleep to avoid concurrent access to database at startup
                    sleep(1)
            # we wait until an exception arises
            wait(process_status,return_when=FIRST_EXCEPTION)

if __name__ == '__main__':

    # prevent launching two harness_service_launcher
    res = Tools.get_pid("harness_service_launcher")
    if len(res) > 1:
        raise RuntimeError("harness_service_launcher already running.")

    # Set the process name to harness_service_launcher
    setproctitle("harness_service_launcher")

    logger = get_logger()

    # kill pid of already existing process
    for process in ["harness_difmet_sender",
                    "harness_file_manager",
                    "harness_ack_receiver"]:
        pid_killed = Tools.kill_process(process)
        for pid in pid_killed:
            logger.info("Killed process %s with pid %i", process,pid)

    # launch the harness
    launch(launch_logger = logger, debug=DEBUG)


