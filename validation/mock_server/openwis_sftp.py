"""sftpserver

https://github.com/rspivak/sftpserver

"""

from OpenSSL import crypto
import subprocess
from multiprocessing import Process
import shlex
from time import sleep
import shutil
import paramiko
import os
from os.path import join
import tempfile
from sftpserver import start_server, PORT, HOST
from tempfile import gettempdir, TemporaryDirectory
from utils.tools import Tools
import sftpserver


class SFTPserver:

    _process = None
    _stagingpost = None
    key_file = None

    @classmethod
    def create_server(cls, stagingpost):

        if cls._process is not None:
            cls._process.terminate()

        # create crypto key
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)

        cls.key_file = key_file = join(gettempdir(), "openwis_sftp_key_test.key")

        with open(key_file ,"wb") as file_:
            data =(crypto.dump_privatekey(crypto.FILETYPE_PEM, k)).decode("utf-8")
            data =bytearray(data.replace("PRIVATE KEY", "RSA PRIVATE KEY"), encoding="utf-8")
            file_.write(data)


        cls._stagingpost = stagingpost
        for i in range(10):
            with open(join(stagingpost,"A_SNFR30LFPW270700_C_LFPW_20180927070000_%i.txt" % i),"w") as file_out:
                file_out.write("truc")

        # os.chdir(gettempdir())
        os.chdir("/")
        args = shlex.split("sftpserver -k {key} -l DEBUG".format(key=key_file))

        # cls._process = Process(sftpserver.start_server(host='localhost', port=3373, keyfile=key_file, level='INFO'))
        # cls._process.start()
        cls._process = subprocess.Popen(args)

        sleep(1)

        # return cls._process, cls._stagingpost

    @classmethod
    def stop_server(cls):
        cls._process.terminate()

    @classmethod
    def wait(cls, t=300):
        try:
            SFTPserver._process.wait(timeout=t)
        except subprocess.TimeoutExpired:
            print("Timeout %s expired" % str(t))
            cls.stop_server()

if __name__ == '__main__':

    with TemporaryDirectory(prefix="harnais_") as stagingpost:
        try:
            SFTPserver.create_server(stagingpost)
            SFTPserver.wait()
        except KeyboardInterrupt:
            SFTPserver.stop_server()


# SFTPserver.create_server("/tmp/")

# # pkey = paramiko.RSAKey.from_private_key_file('/tmp/openwis_sftp_key_test.key')
# transport = paramiko.Transport(('localhost', 22))
# # transport.connect(username='admin', password='admin', pkey=pkey)
# transport.connect(username='admin', password='admin')
# sftp = paramiko.SFTPClient.from_transport(transport)
# print(sftp.listdir('.'))

# SFTPserver.stop_server()

#     # pkey = paramiko.RSAKey.from_private_key_file('/tmp/openwis_sftp_key_test.key')
#     ssh = paramiko.SSHClient()
#     # ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     connectiona_info = dict(hostname = 'localhost', port=3373, username='admin',
#                             # password='admin', pkey=pkey)
#                             password='admin')
#     # >>> import paramiko
#     pkey = paramiko.RSAKey.from_private_key_file('/tmp/openwis_sftp_key_test.key')
#     transport = paramiko.Transport(('localhost', 3373))
#     transport.connect(username='admin', password='admin', pkey=pkey)
#     sftp = paramiko.SFTPClient.from_transport(transport)
#     print(sftp.listdir('.'))

# process.terminate()




