import unittest
import os
from os.path import join
import json
import socket
from utils.const import ENV, PORT, REQ_STATUS
import yaml
from zeep import Client
from tempfile import mkdtemp, gettempdir
import tempfile
from settings.settings_manager import SettingsManager
from validation.mock_server.soap_server import SoapServer
from shutil import rmtree
from os.path import join
from utils.database import Database
from utils.setup_tree import HarnessTree

class TestSoapInterface(unittest.TestCase):

    def setUp(self):


        self.tmpdir  = mkdtemp(prefix='harnais_')
        os.environ["TMPDIR"] = self.tmpdir
        self.staging_post = join(self.tmpdir, "staging_post")
        os.mkdir(self.staging_post)
        # prepare settings
        SettingsManager.load_settings()
        SettingsManager.update(dict(harnaisLogdir=self.tmpdir,
                                harnaisDir=self.tmpdir,
                                harnaisAckDir=self.tmpdir
                                ), testing=True)

        os.environ[ENV.settings] = join(self.tmpdir, "settings_testing.yaml")


        with open(os.environ[ENV.settings], "w") as file_:
            yaml.dump(SettingsManager._parameters, file_)

        SoapServer.create_server()
        self.hostname = hostname = socket.gethostname()
        port = os.environ.get(ENV.port) or PORT
        os.environ[ENV.soap_url] = ('http://{hostname}:{port}/harnais-diss-v2/'
                                    'webservice/Dissemination?wsdl'.format(hostname=hostname,
                                    port=port))
        self.client = Client(os.environ[ENV.soap_url])
        self.factory = self.client.type_factory('http://dissemination.harness.openwis.org/')


    def test_notification_mail(self):

        test_diffusion = self.factory.MailDiffusion(address="dummy@dummy.com",
                                                   headerLine="dummyHeaderLine",
                                                   subject= "dummySubject",
                                                   dispatchMode = "TO",
                                                   attachmentMode="AS_ATTACHMENT")

        info = self.factory.DisseminationInfo(priority=5,SLA=6,
                                              dataPolicy="dummyDataPolicy",
                                              diffusion=test_diffusion)
        result = self.client.service.disseminate(requestId="123456",
                                                 fileURI=self.staging_post,
                                                 disseminationInfo=info)
        self.assertEqual(result.requestStatus, REQ_STATUS.ongoing)
        self.assertEqual(result.requestId, '123456')
        self.assertEqual(result.message, 'dissemination request received')

    def test_notification_ftp(self):

        test_diffusion = self.factory.FTPDiffusion(host="dummyHost",
                                                   port="dummyPort",
                                                   user="dummyUser",
                                                   password="dummyPwd",
                                                   passive="False",
                                                   remotePath="dummyPath",
                                                   checkFileSize="True",
                                                   encrypted="False")

        info = self.factory.DisseminationInfo(priority=5,SLA=6,
                                              dataPolicy="dummyDataPolicy",
                                              diffusion=test_diffusion)
        result = self.client.service.disseminate(requestId="123456",
                                                 fileURI=self.staging_post,
                                                 disseminationInfo=info)
        self.assertEqual(result.requestStatus, REQ_STATUS.ongoing)
        self.assertEqual(result.requestId, '123456')
        self.assertEqual(result.message, 'dissemination request received')

    def test_database_status(self):

        test_diffusion = self.factory.MailDiffusion(address="dummy@dummy.com",
                                                   headerLine="dummyHeaderLine",
                                                   subject= "dummySubject",
                                                   dispatchMode = "TO",
                                                   attachmentMode="AS_ATTACHMENT")

        info = self.factory.DisseminationInfo(priority=5,SLA=6,
                                              dataPolicy="dummyDataPolicy",
                                              diffusion=test_diffusion)
        result = self.client.service.disseminate(requestId="123456",
                                                 fileURI=self.staging_post,
                                                 disseminationInfo=info)

        self.assertEqual(Database.get_request_status("123456"), REQ_STATUS.ongoing)

    def test_json_file(self):

        test_diffusion = self.factory.MailDiffusion(address="dummy@dummy.com",
                                                   headerLine="dummyHeaderLine",
                                                   subject= "dummySubject",
                                                   dispatchMode = "TO",
                                                   attachmentMode="AS_ATTACHMENT")

        info = self.factory.DisseminationInfo(priority=5,SLA=6,
                                              dataPolicy="dummyDataPolicy",
                                              diffusion=test_diffusion)
        self.client.service.disseminate(requestId="123456",
                                                 fileURI=self.staging_post,
                                                 disseminationInfo=info)

        res_dir = HarnessTree.get("temp_dissRequest_A")

        json_file = join(res_dir, os.listdir(res_dir)[0])

        with open(json_file, "r") as file_:
            info_file = json.load(file_)
        dict_ref = {'hostname': self.hostname,
                    'uri': self.staging_post,
                    'req_id': '123456', 'diffpriority': 81,
                    'date': info_file["date"],
                    'diffusion': {'fileName': None,
                                  'attachmentMode': 'AS_ATTACHMENT',
                                  'dispatchMode': 'TO',
                                  'DiffusionType': 'EMAIL',
                                  'subject': 'dummySubject',
                                  'headerLine':
                                  'dummyHeaderLine',
                                  'address': 'dummy@dummy.com'}
                                  }

        self.assertEqual(info_file, dict_ref)

    def tearDown(self):
        rmtree(self.tmpdir)
        SoapServer.stop_server()
        os.environ.pop(ENV.settings)
        os.environ.pop("TMPDIR")
        tempfile.tempdir = None
        Database.reset()
        SettingsManager.reset()


if __name__ == "__main__":
    unittest.main()