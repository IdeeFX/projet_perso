from webservice.server import application
import webservice
import subprocess
from time import sleep
from utils.tools import Tools
import os


class SoapServer:

    _process = None

    @classmethod
    def create_server(cls):
        if cls._process is None:
            #check if no other server is running. if so, kill them
            Tools.kill_process("harness_soap_server")
            # args =["python3", "-m", "webservice.server.application"]

            args =["python3", application.__file__]
            my_env = os.environ.copy()
            my_env["PYTHONPATH"] = os.environ["PYTHONPATH"] + ":" + "/".join(webservice.__path__[0].split('/')[:-1])
            cls._process = subprocess.Popen(args, env=my_env)
            sleep(3)
            print("Soap server started")

    @classmethod
    def stop_server(cls):
        if cls._process is not None:
            cls._process.terminate()
            sleep(1)
            print("Soap server stopped")
            cls._process = None

    @classmethod
    def wait(cls, t=300):
        try:
            SoapServer._process.wait(timeout=t)
        except subprocess.TimeoutExpired:
            print("Timeout %s expired" % str(t))
            cls.stop_server()


if __name__ == '__main__':
    try:
        SoapServer.create_server()
        SoapServer.wait()
    except KeyboardInterrupt:
        SoapServer.stop_server()



