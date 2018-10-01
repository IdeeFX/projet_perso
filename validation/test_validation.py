import socket
import os
from zeep import Client
from utils.const import PORT
from validation.mock_server.soap_server import SoapServer

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
test_uri = "d25c6c87eb567443a45f279df0ba208e/2018/08-30/request/b2400d722042e7b2936fb0d55fab9f39/"
result = client.service.disseminate(requestId="123456", fileURI=test_uri, disseminationInfo=info)

print(client.service.monitorDissemination(requestId="123456"))

SoapServer.stop_server()

