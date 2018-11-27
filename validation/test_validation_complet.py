import socket
import os
from os.path import join
from validation.mock_server.openwis_sftp import SFTPserver
from zeep import Client
from threading import Thread
import unittest
import yaml
from time import sleep
from shutil import rmtree
from distutils.util import strtobool
import tempfile
from tempfile import mkdtemp, gettempdir
from validation.mock_server.soap_server import SoapServer
from validation.mock_server.difmet_ftp import FTPserver
from file_manager.manager import FileManager
from file_sender.sender import DifmetSender
from ack_receiver.ack_receiver import AckReceiver
from settings.settings_manager import SettingsManager, DebugSettingsManager
from utils.setup_tree import HarnessTree
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from webservice.server.application import APP
from utils.const import PORT, ENV
from utils.tools import Tools
from utils.database import Database, Diffusion
from utils.log_setup import setup_logging


class CompleteTest(unittest.TestCase):

    def setUp(self):

        DebugSettingsManager.debug = "False"
        DebugSettingsManager.test_sftp = "True"
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

        # create files on staging post
        for i in range(2):
            with open(join(self.staging_post,"A_SNFR30LFPW270700_C_LFPW_20180927070000_%i.txt" % i),"w") as file_out:
                file_out.write("Dummy staging post test file")



        self.hostname = hostname = socket.gethostname()
        self.port = port = os.environ.get(ENV.port) or PORT
        self.soap_url = os.environ[ENV.soap_url]= ('http://{hostname}:{port}/harnais-diss-v2/'
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
            yaml.dump(dict(SettingsManager._parameters), file_)
        SettingsManager.reset()

    def test_complet(self):
        SettingsManager.load_settings()
        SoapServer.create_server()
        client = Client(self.soap_url)
        factory = client.type_factory('http://dissemination.harness.openwis.org/')

        test_diffusion = factory.MailDiffusion(address="dummy@dummy.com",
                                                headerLine="dummyHeaderLine",
                                                subject= "dummySubject",
                                                dispatchMode = "TO",
                                                attachmentMode="AS_ATTACHMENT")
        
        info = factory.DisseminationInfo(priority=5,SLA=6,dataPolicy="dummyDataPolicy", diffusion=test_diffusion)

        
        result1 = client.service.disseminate(requestId="123456", fileURI=self.staging_post, disseminationInfo=info)
        result2 = client.service.disseminate(requestId="654321", fileURI=self.staging_post, disseminationInfo=info)
        test_diffusion = factory.FTPDiffusion(host="dummyHost",
                                                   port="dummyPort",
                                                   user="dummyUser",
                                                   password="dummyPwd",
                                                   passive="False",
                                                   remotePath="dummyPath",
                                                   checkFileSize="True",
                                                   encrypted="False")

        info = factory.DisseminationInfo(priority=5,SLA=6,
                                              dataPolicy="dummyDataPolicy",
                                              diffusion=test_diffusion)
        result3 = client.service.disseminate(requestId="111111", fileURI=self.staging_post, disseminationInfo=info)

        print(result1)
        print(result2)
        print(result3)

        SoapServer.stop_server()

        SFTPserver.create_server(self.staging_post)
        SettingsManager.update(dict(openwisStagingPath=gettempdir(),
                                    openwisHost="localhost",
                                    openwisSftpUser="admin",
                                    openwisSftpPassword="admin",
                                    openwisSftpPort = 3373
                                    ),
                                testing=True)
        thr = Thread(target=FileManager.process, kwargs={"max_loops":1})

        try:
            thr.start()
            thr.join()
            SFTPserver.stop_server()
            print("Manager finished")
        except KeyboardInterrupt:
            SFTPserver.stop_server()

        sleep(10)

        Tools.kill_process("diffmet_test_ftp_server")
        FTPserver.create_server("/")

        thr = Thread(target=DifmetSender.process, kwargs={"max_loops":3})

        try:
            thr.start()
            thr.join()
            print("DifMet finished")
            FTPserver.stop_server()
        except KeyboardInterrupt:
            FTPserver.stop_server()

        with Database.get_app().app_context():
            records = Diffusion.query.filter(Diffusion.fullrequestId.contains("123456")).all()
        print(records[0].fullrequestId)
        ext_id1 = records[0].diff_externalid
        ext_id2 = records[1].diff_externalid



        with open(join(self.ack_dir, "ack_file.acqdifmet.xml"),"w") as file_:
            file_.write("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
                        "<acquittements>\n"
                        "<acquittement>\n"
                            "<date>2018-10-01T12:31:46Z</date>\n"
                            "<type>RECEIVED</type>\n"
                            "<status>OK</status>\n"
                            "<productid>fr-met,SNFR30LFPW011000LFPW,00000-wiss,20181001100000</productid>\n"
                            "<product_internalid>66180_20181001123146</product_internalid>\n"
                            "<send2>0</send2>\n"
                            "<diffusion_externalid>{ext_id1}</diffusion_externalid>\n"
                            "<diffusion_internalid>66181_20181001123146</diffusion_internalid>\n"
                            "<channel>EMAIL</channel>\n"
                            "<media>EMAIL</media>\n"
                            "<use_standby>0</use_standby>\n"
                            "<email_adress>yves.goupil@meteo.fr</email_adress>\n"
                        "</acquittement>\n"
                        "<acquittement>\n"
                            "<date>2018-10-01T12:31:46Z</date>\n"
                            "<type>SEND</type>\n"
                            "<status>OK</status>\n"
                            "<productid>fr-met,SNFR30LFPW011000LFPW,00001-wiss,20181001100000</productid>\n"
                            "<product_internalid>66180_20181001123146</product_internalid>\n"
                            "<send2>0</send2>\n"
                            "<diffusion_externalid>{ext_id2}</diffusion_externalid>\n"
                            "<diffusion_internalid>66181_20181001123146</diffusion_internalid>\n"
                            "<channel>EMAIL</channel>\n"
                            "<media>EMAIL</media>\n"
                            "<use_standby>0</use_standby>\n"
                            "<try_number>1</try_number>\n"
                            "<email_adress>yves.goupil@meteo.fr</email_adress>\n"
                            "<comment>nom de fichier en attachement au courriel: machin</comment>\n"
                        "</acquittement>\n"
                        "<acquittement>\n"
                            "<date>2018-10-01T12:31:46Z</date>\n"
                            "<type>SEND</type>\n"
                            "<status>OK</status>\n"
                            "<productid>fr-met,SNFR30LFPW011000LFPW,00000-wiss,20181001100000</productid>\n"
                            "<product_internalid>66180_20181001123146</product_internalid>\n"
                            "<send2>0</send2>\n"
                            "<diffusion_externalid>{ext_id1}</diffusion_externalid>\n"
                            "<diffusion_internalid>66181_20181001123146</diffusion_internalid>\n"
                            "<channel>EMAIL</channel>\n"
                            "<media>EMAIL</media>\n"
                            "<use_standby>0</use_standby>\n"
                            "<try_number>1</try_number>\n"
                            "<email_adress>yves.goupil@meteo.fr</email_adress>\n"
                            "<comment>nom de fichier en attachement au courriel: machin</comment>\n"
                        "</acquittement>\n"
                        "<acquittementnumber>3</acquittementnumber>\n"
                        "</acquittements>".format(ext_id1=ext_id1, ext_id2=ext_id2))

        thr = Thread(target=AckReceiver.process, kwargs={"max_loops":2})

        thr.start()
        thr.join()
        print("Ack_receiver finished")

        # check acquittement
        SoapServer.create_server()
        client = Client(self.soap_url)
        factory = client.type_factory('http://dissemination.harness.openwis.org/')
        result = client.service.monitorDissemination(requestId="123456")
        print(result)
        result = client.service.monitorDissemination(requestId="654321")
        print(result)
        SoapServer.stop_server()

        error_log = join(self.tmpdir, "harnais/errors.log")

        with open(error_log, "r") as file_:
            self.assertEqual(file_.read(),"")
        

    def tearDown(self):
        cleared = Tools.move_dir_to_trash_can(self.tmpdir)
        if not cleared:
            rmtree(self.tmpdir)
        os.environ.pop(ENV.settings)
        os.environ.pop("TMPDIR")
        os.environ.pop(ENV.soap_url)
        tempfile.tempdir = None
        Database.reset()
        SettingsManager.reset()
        DebugSettingsManager.reset()

if __name__ == "__main__":
    unittest.main()
