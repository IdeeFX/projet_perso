import random
import hashlib
import string
import os
import shutil
import signal
from subprocess import check_output, CalledProcessError
from utils.const import RANDOM_ID_LENGTH

class Tools:

    @staticmethod
    def generate_random_string(length=RANDOM_ID_LENGTH):

        # objective is ^[a-zA-Z0-9][a-zA-Z0-9_,+\\.-]+$'
        rand = random.SystemRandom()
        char = string.ascii_letters + string.digits
        res = rand.choice(char)
        # res += ''.join(rand.choice(char + "_,+\\.-") for _ in range(length-1))
        res += ''.join(rand.choice(char) for _ in range(length-1))

        return res

    @staticmethod
    def checksum_file(file_path):

        with open(file_path, "rb") as file_:
            content = file_.read()
            checksum = hashlib.sha256(content).digest()[:16]

        return checksum

    @staticmethod
    def get_pid(name):
        my_env = os.environ.copy()
        my_env["PATH"] = "/usr/bin:/sbin:" + my_env["PATH"]
        try:
            res = list(map(int,check_output(["pidof",name],
                                            env=my_env).split()
                           )
                      )
        except CalledProcessError:
            res = []

        return res

    @staticmethod
    def kill_process(process):
        pid_to_kill = Tools.get_pid(process)
        for pid in pid_to_kill:
            os.kill(pid, signal.SIGTERM)
        return pid_to_kill

    @staticmethod
    def remove_file(file_path, file_tag, logger):
        rep = os.environ.get("MFSERV_HARNESS_TRASH")
        try:
            is_dir = os.path.isdir(rep)
        except TypeError:
            logger.error("Value of environment variable MFSERV_HARNESS_TRASH"
                         "is not a path to a directory.")
            is_dir = False

        if is_dir:
            shutil.move(file_path, rep)
            logger.debug("%s file %s moved to %s", file_tag, file_path, rep)
        else:
            logger.debug("Deleting %s file %s.", file_tag, file_path)
            os.remove(file_path)

    @staticmethod
    def clear_trash_can():
        rep = os.environ.get("MFSERV_HARNESS_TRASH")
        try:
            is_dir = os.path.isdir(rep)
        except TypeError:
            logger.error("Value of environment variable MFSERV_HARNESS_TRASH"
                         "is not a path to a directory.")
            is_dir = False

        if is_dir:
            for file_ in os.listdir(rep):
                os.remove(os.path.join(rep, file_))


class Incrementator:
    idx = 0

    @classmethod
    def get_incr(cls):

        cls.idx = int(cls.idx % 1e5)

        incr = str(cls.idx)

        while len(incr) < 5:
            incr = "0" + incr

        cls.idx += 1

        return incr
