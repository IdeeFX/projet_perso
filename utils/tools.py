import random
import hashlib
import string
import os
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
        res += ''.join(rand.choice(char + "_,+\\.-") for _ in range(length-1))

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
