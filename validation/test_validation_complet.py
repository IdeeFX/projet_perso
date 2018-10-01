import socket
import os
from os.path import join
from validation.mock_server.openwis_sftp import SFTPserver
from zeep import Client
# from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from threading import Thread
from time import sleep
from tempfile import TemporaryDirectory, gettempdir
from launcher import launch
from validation.mock_server.soap_server import SoapServer
from validation.mock_server.difmet_ftp import FTPserver
from file_manager.manager import FileManager
from file_sender.sender import DifmetSender
from settings.settings_manager import SettingsManager, DebugSettingsManager
from utils.setup_tree import HarnessTree
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from webservice.server.application import APP
from utils.const import PORT
from utils.tools import Tools
from utils.database import Database


Database.initialize_database(APP)
Database.refresh(**{})
#clear files
dir_A = HarnessTree.get("temp_dissRequest_A")
dir_B = HarnessTree.get("temp_dissRequest_B")
dir_C = HarnessTree.get("temp_dissRequest_C")

def clear_dir(dir_):
    for item in os.listdir(dir_):
        os.remove(join(dir_, item))

for dir_ in [dir_A,dir_B,dir_C]:
    clear_dir(dir_)


SoapServer.create_server()

hostname = socket.gethostname()
port = os.environ.get("MFSERV_NGINX_PORT") or PORT
client = Client('http://{hostname}:{port}/harnais-diss-v2/'
                'webservice/Dissemination?wsdl'.format(hostname=hostname,
                                                       port=port))
#client = Client('http://wisauth-int-p.meteo.fr:8080/harnais-diss-v2/webservice/Dissemination?wsdl')
factory = client.type_factory('http://dissemination.harness.openwis.org/')

testDiffusion = factory.MailDiffusion(address="dummy@dummy.com",
                                        headerLine="dummyHeaderLine",
                                        subject= "dummySubject",
                                        dispatchMode = "TO",
                                        attachmentMode="AS_ATTACHMENT")
info = factory.DisseminationInfo(priority=5,SLA=6,dataPolicy="dummyDataPolicy", diffusion=testDiffusion)
with TemporaryDirectory(prefix="harnais_") as stagingpost:
    print(stagingpost)
    result = client.service.disseminate(requestId="123456", fileURI=stagingpost, disseminationInfo=info)
    result = client.service.disseminate(requestId="654321", fileURI=stagingpost, disseminationInfo=info)
    # result = client.service.disseminate(requestId="654321", fileURI=stagingpost, disseminationInfo=info)
    # print(result)

    SoapServer.stop_server()

    #start sftp server
    SFTPserver.create_server(stagingpost)
    SettingsManager.update(dict(openwisStagingPath=gettempdir(),
                                openwisHost="localhost",
                                openwisSftpUser="admin",
                                # openwisSftpUser="openwis",
                                openwisSftpPassword="admin",
                                openwisSftpPort = 3373
                                ),
                            testing=True)
    DebugSettingsManager.sftp_pool = ThreadPool
    # DebugSettingsManager.sftp_pool = Pool
    thr = Thread(target=FileManager.process, kwargs={"max_loops":1})
    thr.start()

    try:
        thr.join(60)
        # thr.join()
        # stopping file manager
        FileManager.stop()
        SFTPserver.stop_server()
        print("Manager success")
    except KeyboardInterrupt:
        SFTPserver.stop_server()
sleep(10)
with TemporaryDirectory(prefix="diffmet_") as deposit:
    DebugSettingsManager.ftp_pool = ThreadPool

    Tools.kill_process("diffmet_test_ftp_server")
    FTPserver.create_server("/")
    SettingsManager.update(dict(dissHost="0.0.0.0",
                                dissFtpUser="user",
                                dissFtpPasswd="12345",
                                dissFtpDir=deposit,
                                dissFtpMode=None,
                                dissFtpPort=2121,
                                sendFTPlimitConn=5
                                ),
                            testing=True)
    thr = Thread(target=DifmetSender.process, kwargs={"max_loops":2})

    try:
        thr.start()
        thr.join(80)
        # stopping file manager
        DifmetSender.stop()
        print("DifMet success")
    except KeyboardInterrupt:
        FTPserver.stop_server()

    print("fin")
