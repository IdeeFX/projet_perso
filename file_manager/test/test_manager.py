import unittest
import socket
import os
from os.path import join
import json
import yaml
from utils.const import ENV, REQ_STATUS
from datetime import datetime
from zeep import Client
import tempfile
from tempfile import mkdtemp, gettempdir
import tempfile
from settings.settings_manager import SettingsManager
from validation.mock_server.openwis_sftp import SFTPserver
from shutil import rmtree
from os.path import join
from utils.const import REQ_STATUS
from utils.database import Database, Diffusion
from utils.setup_tree import HarnessTree
from utils.tools import Tools
from utils.log_setup import setup_logging
from file_manager.manager import FileManager

class TestFileManager(unittest.TestCase):

    def setUp(self):

        self.tmpdir  = mkdtemp(prefix='harnais_')
        os.environ["TMPDIR"] = self.tmpdir
        self.staging_post = join(self.tmpdir, "staging_post")
        os.mkdir(self.staging_post)
        # # prepare settings
        SettingsManager.load_settings()
        SettingsManager.update(dict(harnaisLogdir=self.tmpdir,
                                    harnaisDir=self.tmpdir,
                                    harnaisAckDir=self.tmpdir,
                                    openwisStagingPath=gettempdir(),
                                    openwisHost="localhost",
                                    openwisSftpUser="admin",
                                    openwisSftpPassword="admin",
                                    openwisSftpPort = 3373
                                   ), testing=True)

        os.environ[ENV.settings] = join(self.tmpdir, "settings_testing.yaml")

        with open(os.environ[ENV.settings], "w") as file_:
            yaml.dump(SettingsManager._parameters, file_)

        setup_logging()

        for i in range(10):
            with open(join(self.staging_post,"A_SNFR30LFPW270700_C_LFPW_20180927070000_%i.txt" % i),"w") as file_out:
                file_out.write("Dummy staging post test file")

        SFTPserver.create_server(self.staging_post)

        # create json file
        self.dir_a = HarnessTree.get("temp_dissRequest_A")
        self.json_file = json_file = join(self.dir_a, "test_instruction_file.json")
        instr = {'hostname': socket.gethostname(),
                 'uri': self.staging_post,
                 'req_id': '123456', 'diffpriority': 81,
                 'date': datetime.now().strftime("%Y%m%d%H%M%S"),
                 'diffusion': {'fileName': None,
                               'attachmentMode': 'AS_ATTACHMENT',
                               'dispatchMode': 'TO',
                               'DiffusionType': 'EMAIL',
                               'subject': 'dummySubject',
                               'headerLine':
                               'dummyHeaderLine',
                               'address': 'dummy@dummy.com'}
                               }
        with open(json_file, "w") as file_:
            json.dump(instr, file_)
        # create corresponding record in database:
        ext_id = Tools.generate_random_string()
        diffusion = Diffusion(diff_externalid=ext_id,
                              fullrequestId="123456"+socket.gethostname(),
                              requestStatus=REQ_STATUS.ongoing,
                              Date=datetime.now(),
                              rxnotif=True,
                              message="Created record in SQL database")

        with Database.get_app().app_context():
            database = Database.get_database()
            database.session.add(diffusion)
            database.session.commit()

    def test_download_staging_post(self):

        # FileManager.process_instruction_file(self.json_file)

        print("ok")



    def tearDown(self):
        rmtree(self.tmpdir)
        SFTPserver.stop_server()
        os.environ.pop(ENV.settings)
        os.environ.pop("TMPDIR")
        tempfile.tempdir = None
        Database.reset()
        SettingsManager.reset()



if __name__ == "__main__":
    unittest.main()