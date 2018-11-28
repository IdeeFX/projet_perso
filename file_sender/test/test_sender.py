import unittest
import os
from os.path import join, isfile
import json
import yaml
from time import sleep
from utils.const import ENV
from re import match
import tempfile
from tempfile import mkdtemp, gettempdir
import tempfile
from settings.settings_manager import SettingsManager
from validation.mock_server.difmet_ftp import FTPserver
from shutil import rmtree
from utils.setup_tree import HarnessTree
from utils.tools import Tools
from utils.log_setup import setup_logging
from file_sender.sender import DifmetSender
import file_sender.sender
import utils.const

class TestFileManager_SFTP(unittest.TestCase):
    """
    Testing FTP transfers, without hitting a timeout and
    when one big file transfer hits the timeout.
    """

    def setUp(self):

        # Configuring repertories
        file_sender.sender.DEBUG = False
        self.tmpdir  = mkdtemp(prefix='harnais_')
        os.environ["TMPDIR"] = self.tmpdir
        self.difmet_deposit = join(self.tmpdir, "difmet_deposit")
        os.mkdir(self.difmet_deposit)
        self.ack_dir = join(self.tmpdir, "ack_dir")
        os.mkdir(self.ack_dir)

        #killing ftpserver in case one exists
        Tools.kill_process("diffmet_test_ftp_server")
        # start FTP server
        FTPserver.create_server("/")

    # def test_sending_timeout(self):
    #     """
    #     Testing FTP transfer of 4 very small files and one big file.
    #     Small files still get transfered despite small timeout because 
    #     process can't be closed quick enough but the big file get stuck 
    #     half way as required.

    #     Currently deactivated because i can't find the right way to surchage
    #     TIMEOUT_BUFFER at 0 properly.
    #     """
        

    #     # prepare settings
    #     SettingsManager.load_settings()
    #     SettingsManager.update(dict(harnaisLogdir=self.tmpdir,
    #                                 harnaisDir=self.tmpdir,
    #                                 harnaisAckDir=self.tmpdir,
    #                                 dissHost="0.0." + "0.0",
    #                                 dissFtpUser="user",
    #                                 dissFtpPasswd="12345",
    #                                 dissFtpDir=self.difmet_deposit,
    #                                 bandwidth=100000,
    #                                 dissFtpMode=None,
    #                                 dissFtpPort=2121,
    #                                 sendFTPlimitConn=5,
    #                                 sendFTPIdle=10)
    #                                 , testing=True)

    #     os.environ[ENV.settings] = join(self.tmpdir, "settings_testing.yaml")

    #     with open(os.environ[ENV.settings], "w") as file_:
    #         yaml.dump(SettingsManager._parameters, file_)

    #     setup_logging()

    #     SettingsManager.load_settings()
    #     dir_C = HarnessTree.get("temp_dissRequest_C")
    #     dir_D = HarnessTree.get("temp_dissRequest_D")

    #     #create dummy files to send 
    #     for i in range(5):
    #         filename = "package_file_%i.tar.gz" % i
    #         with open(join(dir_C,filename),"wb") as file_out:
    #             if i==2:
    #                 # One file of size 500 Mo 
    #                 size = 500 * (1<<20)
    #             else:
    #                 # Files of size 1000 bits 
    #                 size = 1000
    #             file_out.seek(size-1)
    #             file_out.write(b"\0")
    #     DifmetSender.process(max_loops=3)
    #     sleep(SettingsManager.get("sendFTPIdle"))

    #     list_dwld = ['package_file_0.tar.gz', 'package_file_2.tar.gz.tmp', 
    #                  'package_file_4.tar.gz', 'package_file_1.tar.gz',
    #                  'package_file_3.tar.gz']
    #     expected_result = True
    #     for file_ in os.listdir(self.difmet_deposit):
    #         expected_result = expected_result and (file_ in list_dwld)
        
    #     self.assertTrue(expected_result)

    def test_sending(self):
        """
        Testing FTP transfer of 5 small files
        """

        # prepare settings
        SettingsManager.load_settings()
        SettingsManager.update(dict(harnaisLogdir=self.tmpdir,
                                    harnaisDir=self.tmpdir,
                                    harnaisAckDir=self.tmpdir,
                                    dissHost="0.0." + "0.0",
                                    dissFtpUser="user",
                                    dissFtpPasswd="12345",
                                    bandwidth=10,
                                    dissFtpDir=self.difmet_deposit,
                                    dissFtpMode=None,
                                    dissFtpPort=2121,
                                    sendFTPlimitConn=5,
                                    sendFTPIdle=10)
                                    , testing=True)

        os.environ[ENV.settings] = join(self.tmpdir, "settings_testing.yaml")

        with open(os.environ[ENV.settings], "w") as file_:
            yaml.dump(SettingsManager._parameters, file_)

        setup_logging()

        SettingsManager.load_settings()
        dir_C = HarnessTree.get("temp_dissRequest_C")
        dir_D = HarnessTree.get("temp_dissRequest_D")

        #create dummy files of size 1000 bits  to send
        for i in range(5):
            filename = "package_file_%i.tar.gz" % i
            with open(join(dir_C,filename),"wb") as file_out:
                size = 1000
                file_out.seek(size-1)
                file_out.write(b"\0")
        DifmetSender.process(max_loops=3)

        list_dwld = ['package_file_0.tar.gz', 'package_file_2.tar.gz', 
                     'package_file_4.tar.gz', 'package_file_1.tar.gz',
                     'package_file_3.tar.gz']
        expected_result = True
        for file_ in os.listdir(self.difmet_deposit):
            expected_result = expected_result and (file_ in list_dwld)
        
        self.assertTrue(expected_result)

    def tearDown(self):
        #stopping FTP server
        FTPserver.stop_server()
        #clearing repertories
        cleared = Tools.move_dir_to_trash_can(self.tmpdir)
        if not cleared:
            rmtree(self.tmpdir)
        # cleaning up environment
        os.environ.pop(ENV.settings)
        os.environ.pop("TMPDIR")
        tempfile.tempdir = None
        SettingsManager.reset()
        HarnessTree.reset()
        



if __name__ == "__main__":
    unittest.main()