from webservice.server import application
import subprocess
from time import sleep
from utils.tools import Tools


class SoapServer:

    _process = None

    @classmethod
    def create_server(cls):
        if cls._process is None:
            #check if no other server is running. if so, kill them
            Tools.kill_process("harness_soap_server")
            args =["python3", "-m", "webservice.server.application"]
            cls._process= subprocess.Popen(args)
            sleep(3)
            print("Soap server started")

    @classmethod
    def stop_server(cls):
        if cls._process is not None:
            cls._process.terminate()
            sleep(1)
            print("Soap server stopped")

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



