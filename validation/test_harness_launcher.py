from harness_launcher import launch
import unittest
from threading import Thread
from settings.settings_manager import SettingsManager, DebugSettingsManager
import os
from os.path import join
import tempfile
from tempfile import mkdtemp, gettempdir
import socket
from utils.log_setup import setup_logging
import yaml
from utils.database import Database
from utils.const import PORT, ENV
from multiprocessing import Process
from shutil import rmtree
import logging

class CompleteTest(unittest.TestCase):

    def setUp(self):


        self.tmpdir  = mkdtemp(prefix='harnais_')
        harnais_dir = join(self.tmpdir, "harnais")
        os.mkdir(harnais_dir)
        os.environ["TMPDIR"] = self.tmpdir
        self.staging_post = join(self.tmpdir, "staging_post")
        os.mkdir(self.staging_post)
        self.difmet_deposit = join(self.tmpdir, "difmet_deposit")
        os.mkdir(self.difmet_deposit)
        self.ack_dir = join(self.tmpdir, "ack_dir")
        os.mkdir(self.ack_dir)


        self.hostname = hostname = socket.gethostname()
        port = os.environ.get(ENV.port) or PORT
        os.environ[ENV.soap_url] = ('http://{hostname}:{port}/harnais-diss-v2/'
                                    'webservice/Dissemination?wsdl'.format(hostname=hostname,
                                    port=port))

        SettingsManager.load_settings()
        SettingsManager.update(dict(harnaisLogdir=harnais_dir,
                                    harnaisDir=harnais_dir,
                                    harnaisAckDir=self.ack_dir,
                                    openwisStagingPath=gettempdir(),
                                    openwisHost="localhost",
                                    openwisSftpUser="admin",
                                    openwisSftpPassword="admin",
                                    openwisSftpPort = 3373,
                                    processFileIdle = 10,
                                    dissHost="0.0." + "0.0",
                                    dissFtpUser="user",
                                    dissFtpPasswd="12345",
                                    dissFtpDir=self.difmet_deposit,
                                    dissFtpMode=None,
                                    dissFtpPort=2121,
                                    sendFTPlimitConn=5),
                               testing=True)

        os.environ[ENV.settings] = join(self.tmpdir, "settings_testing.yaml")

        with open(os.environ[ENV.settings], "w") as file_:
            yaml.dump(SettingsManager._parameters, file_)

        setup_logging()


    def test_harness_launch(self):


        launcher = Process(target=launch)
        launcher.start()
        launcher.join(10)
        launcher.terminate()
        error_log = join(self.tmpdir, "errors.log")

        with open(error_log, "r") as file_:
            self.assertEqual(file_.read(),"")
        



    def tearDown(self):
        rmtree(self.tmpdir)
        os.environ.pop(ENV.settings)
        os.environ.pop("TMPDIR")
        tempfile.tempdir = None
        Database.reset()
        SettingsManager.reset()

if __name__ == "__main__":
    unittest.main()
