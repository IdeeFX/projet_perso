"""
https://stackoverflow.com/a/15476842/10104649
"""

import os

from setproctitle import setproctitle
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from tempfile import gettempdir

from multiprocessing import Process

class FTPserver:

    _process = None

    @classmethod
    def create_server(cls, deposit_repertory='.'):


        if cls._process is not None:
            cls._process.terminate()


        cls._process = Process(target=cls.start_server, args = (deposit_repertory,))
        cls._process.start()


    def start_server(deposit_repertory):

        # Instantiate a dummy authorizer for managing 'virtual' users
        authorizer = DummyAuthorizer()

        # Define a new user having full r/w permissions
        authorizer.add_user('user', '12345', deposit_repertory, perm='elradfmwMT')

        # Instantiate FTP handler class
        handler = FTPHandler
        handler.authorizer = authorizer

        # Define a customized banner (string returned when client connects)
        handler.banner = "pyftpdlib based ftpd ready."

        # Specify a masquerade address and the range of ports to use for
        # passive connections.  Decomment in case you're behind a NAT.
        #handler.masquerade_address = '151.25.42.11'
        #handler.passive_ports = range(60000, 65535)

        # Instantiate FTP server class and listen on 0.0.0.0:2121
        address = ('', 2121)
        server = FTPServer(address, handler)

        # set a limit for connections
        server.max_cons = 256
        server.max_cons_per_ip = 5

        # start ftp server
        server.serve_forever()

    @classmethod
    def stop_server(cls):
        cls._process.terminate()

    @classmethod
    def wait(cls, t=300):
        cls._process.join(timeout=t)

if __name__ == '__main__':
    setproctitle("diffmet_test_ftp_server")
    try:
        FTPserver.create_server(gettempdir())
        FTPserver.wait()
    except KeyboardInterrupt:
        FTPserver.stop_server()

    # p = Process(target=main)
    # p.start()
    # # p.join(10)
    # from ftplib import FTP
    # ftp = FTP()
    # ftp.connect("0.0.0.0",2121)
    # ftp.login("user","12345")
    # print(ftp.retrlines('LIST') )

    # p.terminate()