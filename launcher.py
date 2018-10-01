
import logging
import os
import signal
from time import sleep
from distutils.util import strtobool
from concurrent.futures import (ThreadPoolExecutor, ProcessPoolExecutor,
                               ALL_COMPLETED, FIRST_COMPLETED,
                               FIRST_EXCEPTION, wait)
from subprocess import check_output, CalledProcessError
import traceback
from file_manager.manager import FileManager
from file_sender.sender import DifmetSender
from ack_receiver.ack_receiver import AckReceiver
from utils.log_setup import setup_logging
from settings.settings_manager import SettingsManager

# set to True for internal testing outside of production by
# using MFSERV_HARNESS_DEBUG
# It switches the launcher from a process based multiprocessing to
# a thread implementation to follow more easily the overall process
# in a debugger.
try:
    DEBUG = bool(strtobool(os.environ.get("MFSERV_HARNESS_DEBUG") or "False"))
except ValueError:
    DEBUG = False

LOGGER = None

def get_pid(name):
    try:
        res = list(map(int,check_output(["pidof",name])).split())
    except CalledProcessError:
        res = []

    return res

def kill_process(process):
    pid_to_kill = get_pid(process)
    for pid in pid_to_kill:
        os.kill(pid, signal.SIGTERM)
    return pid_to_kill

def get_logger():
    SettingsManager.load_settings()

    # initialize LOGGER
    setup_logging()
    # TODO : create a launcher handler in logging
    logger = logging.getLogger(__name__)
    logger.debug("Logging configuration set up in %s", __name__)
    return logger

def launch(launch_logger=None, debug=True):

    if launch_logger is None:
        launch_logger = get_logger()

    def log_exception(exc, proc, i):
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

    process_status = [None]*3
    proc_list = [DifmetSender.process,
                 FileManager.process,
                 AckReceiver.process]

    with executor_class(max_workers=len(process_status)) as executor:
        #launch the process
        for i, proc in enumerate(proc_list):
            process_status[i] = executor.submit(proc)

        #if one crashes, it get restarted
        while True:
            sleep(10)
            for i, status in enumerate(process_status):
                proc = proc_list[i]
                if not status.running():
                    exc  = status.exception()
                    log_exception(exc, proc, i)
                    process_status[i] = executor.submit(proc)

            # we wait until an exception arises
            wait(process_status,return_when=FIRST_EXCEPTION)

if __name__ == '__main__':

    logger = get_logger()

    # kill pid of previous process
    for process in ["harness_difmet_sender",
                    "harness_file_manager",
                    "harness_ack_receiver"]:
        pid_killed = kill_process(process)
        for pid in pid_killed:
            logger.info("Killed process %s with pid %i", process,pid)


    launch(launch_logger = logger, debug=DEBUG)


