import unittest
import socket
import os
from os.path import join, isfile
import json
import yaml
from utils.const import ENV, REQ_STATUS
from re import match
from datetime import datetime
from zeep import Client
import tempfile
from tempfile import mkdtemp, gettempdir
import tempfile
from settings.settings_manager import SettingsManager, DebugSettingsManager
from validation.mock_server.openwis_sftp import SFTPserver
from shutil import rmtree
from utils.const import REQ_STATUS
from utils.database import Database, Diffusion
from utils.setup_tree import HarnessTree
from utils.tools import Tools
from utils.log_setup import setup_logging
from file_manager.manager import FileManager
import file_manager.manager

class TestFileManager_local(unittest.TestCase):
    """
    Thoses tests check that json files are processed correctly
    and that local copy of files from staging post is done properly.
    """

    def setUp(self):

        # Configuring repertories
        file_manager.manager.TEST_SFTP = False
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

        SFTPserver.create_server(self.staging_post)

        # create json file to process
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
        # put it in cache/A_dissreq
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
        """
        We check that files on staging post get in cache/B_fromstaging
        """
        self.assertFalse(file_manager.manager.TEST_SFTP)

        files_list = []
        for i in range(4):
            filename = "A_SNFR30LFPW270700_C_LFPW_20180927070000_%i.txt" % i
            files_list.append(filename)
            with open(join(self.staging_post,filename),"w") as file_out:
                file_out.write("Dummy staging post test file")

        FileManager.process_instruction_file(self.json_file)

        dir_b = HarnessTree.get("temp_dissRequest_B")

        for filename in files_list:
            self.assertTrue(os.path.isfile(join(dir_b, filename)))




    def test_download_staging_post_zip(self):
        """
        We check that a tmp.zip file on staging post is processed correctly
        when packaged
        """

        self.assertFalse(file_manager.manager.TEST_SFTP)
        
        with open(join(self.staging_post,"tmp.zip"),"w") as file_out:
            file_out.write("Dummy staging post test file")

        FileManager.dir_b = HarnessTree.get("temp_dissRequest_B")
        FileManager.dir_c = HarnessTree.get("temp_dissRequest_C")
        diss_instructions = dict()
        all_files_fetched = []
        process_ok, instructions, files_fetched = FileManager.process_instruction_file(self.json_file)

        if process_ok:
            req_id = instructions["req_id"]
            hostname = instructions["hostname"]
            diss_instructions[req_id+hostname] = instructions
            all_files_fetched += [item for item in files_fetched if
                                    item not in all_files_fetched]

        #process the tmp.zip file by renaming it correctly
        FileManager.package_data(all_files_fetched, diss_instructions)
        dir_c_list = os.listdir(FileManager.dir_c)
        self.assertTrue(len(dir_c_list)>0)
        if len(dir_c_list)>0:
            file_packaged = dir_c_list[0]
            self.assertTrue(match(r'fr-meteo-harnaisdiss,\d+,,\d+.tar.gz', file_packaged) is not None) 

        


    def tearDown(self):
        #clearing repertories
        cleared = Tools.move_dir_to_trash_can(self.tmpdir)
        if not cleared:
            rmtree(self.tmpdir)
        SFTPserver.stop_server()
        os.environ.pop(ENV.settings)
        os.environ.pop("TMPDIR")
        tempfile.tempdir = None
        Database.reset()
        SettingsManager.reset()
        DebugSettingsManager.reset()



if __name__ == "__main__":
    unittest.main()
