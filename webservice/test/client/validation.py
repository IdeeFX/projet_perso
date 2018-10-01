from zeep import Client
import unittest
from subprocess import Popen
from webservice.server import application
from time import sleep
from utils.const import REQ_STATUS

class TestLogging(unittest.TestCase):

    def setUp(self):

        # start server
        # TODO check pour python version
        self.serverProcess = Popen(["python3", application.__file__])
        sleep(5)

        # TODO check status
        # status = sp.Popen.poll(extProc) # status should be 'None'

        # call the client
        # TODO check if port 5000
        self.client = Client('http://localhost:5000/Dissemination?wsdl')
        self.factory = self.client.type_factory('http://dissemination.harness.openwis.org/')

    def test_MailDissemination(self):
        testDiffusion = self.factory.MailDiffusion(address="dummy@dummy.com",
                                               headerLine="dummyHeaderLine",
                                               subject= "dummySubject",
                                               dispatchMode = "TO",
                                               attachmentMode="AS_ATTACHMENT")
        info = self.factory.DisseminationInfo(priority=5,SLA=6,dataPolicy="dummyDataPolicy", diffusion=testDiffusion)
        result = self.client.service.disseminate(requestId="dummyRequestId", fileURI="dummyFileURI", disseminationInfo=info)

        # vérifie le statut
        self.assertEqual((result.requestId, result.message,result.requestStatus),("dummyRequestId","mess_hello",REQ_STATUS.ongoing))



    def tearDown(self):

        Popen.terminate(self.serverProcess)

        # TODO check status
        # status = sp.Popen.poll(extProc) # status should be 'None'

if __name__ == "__main__":
    unittest.main()
