import random
import hashlib
import string
import os
from os.path import join, basename
import shutil
import signal
from subprocess import check_output, CalledProcessError
from utils.const import RANDOM_ID_LENGTH, ENV
from utils.const import DEFAULT_SETTINGS_PATH, ENV
import yaml

class Tools:

    @staticmethod
    def generate_random_string(length=RANDOM_ID_LENGTH):

        # objective is ^[a-zA-Z0-9][a-zA-Z0-9_,+\\.-]+$'
        rand = random.SystemRandom()
        char = string.ascii_letters + string.digits
        res = rand.choice(char)
        res += ''.join(rand.choice(char) for _ in range(length-1))

        return res

    @staticmethod
    def checksum_file(file_path):

        if os.path.isfile(file_path):
            with open(file_path, "rb") as file_:
                content = file_.read()
                checksum = hashlib.sha256(content).digest()[:16]
        else:
            checksum=b"1"

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
        rep = os.environ.get(ENV.trash)
        try:
            is_dir = os.path.isdir(rep)
        except TypeError:
            if rep is not None:
                logger.error("Value of environment variable %s "
                            "is not a path to a directory.", ENV.trash)
            is_dir = False

        if is_dir:
            trash_path = join(rep, basename(file_path))
            if not os.path.isfile(trash_path):
                shutil.move(file_path, rep)
            else:
                os.remove(trash_path)
                shutil.move(file_path, rep)
            logger.debug("%s file %s moved to %s", file_tag, file_path, rep)
        else:
            logger.debug("Deleting %s file %s.", file_tag, file_path)
            os.remove(file_path)

    @staticmethod
    def clear_trash_can():
        rep = os.environ.get(ENV.trash)
        try:
            is_dir = os.path.isdir(rep)
        except TypeError:
            if rep is not None:
                logger.error("Value of environment variable %s "
                            "is not a path to a directory.", ENV.trash)
            is_dir = False

        if is_dir:
            for file_ in os.listdir(rep):
                os.remove(os.path.join(rep, file_))


    @staticmethod
    def ack_str(ack_string):

        ack_string = str(ack_string)

        ack_string = ack_string.replace("&","&amp;")
        ack_string = ack_string.replace("<","&lt;")
        ack_string = ack_string.replace(">","&gt;")
        ack_string = ack_string.replace("\'","&apos;")
        ack_string = ack_string.replace("\"","&quot;")

        return ack_string

    @staticmethod
    def ack_decode(ack_string):

        if ack_string is not None:
            ack_string = ack_string.replace("&amp;", "&",)
            ack_string = ack_string.replace("&lt;", "<",)
            ack_string = ack_string.replace("&gt;", ">",)
            ack_string = ack_string.replace("&apos;", "\'")
            ack_string = ack_string.replace("&quot;", "\"")

        return ack_string

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
