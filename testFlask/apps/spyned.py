from spyne.application import Application
from spyne.decorator import srpc, rpc
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Integer, Unicode, Boolean
# from spyne.protocol.http import HttpRpc
# from spyne.protocol.json import JsonDocument
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication

MailDispatchMode = Unicode(values=['TO', 'CC', 'BCC'])
MailAttachmentMode = Unicode(values=['EMBEDDED_IN_BODY', 'AS_ATTACHMENT'])
requestStatus = Unicode(values=['ONGOING_DISSEMINATION', 'DISSEMINATED', 'FAILED'])
class requestStatus(Unicode):
    class Attributes(Unicode.Attributes):
        values = ['ONGOING_DISSEMINATION', 'DISSEMINATED', 'FAILED']



class Diffusion(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    fileName = Unicode

class FTPDiffusion(Diffusion):

    class Attributes(Diffusion.Attributes):
        exc_interface = True

    __namespace__="http://dissemination.harness.openwis.org/"

    host = Unicode
    port = Unicode
    user = Unicode
    password = Unicode
    passive = Boolean
    remotePath = Unicode
    checkFileSize = Boolean

class MailDiffusion(Diffusion):

    __namespace__="http://dissemination.harness.openwis.org/"

    address = Unicode
    headerLine = Unicode
    subject = Unicode
    dispatchMode = Unicode(values=['TO', 'CC', 'BCC'])
    attachmentMode = Unicode(values=['EMBEDDED_IN_BODY', 'AS_ATTACHMENT'])


class DisseminationStatus(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    requestId = Unicode
    requestStatus = Unicode(values=['ONGOING_DISSEMINATION', 'DISSEMINATED', 'FAILED'])
    message = Unicode

    def __init__(self,  requestId, requestStatus, message):
        # don't forget to call parent class initializer
        super(DisseminationStatus, self).__init__()
        self.requestId = requestId
        self.requestStatus = requestStatus
        self.message = message 

class DisseminateResponse(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    disseminationResult = DisseminationStatus

    def __init__(self,  disseminationResult):
        # don't forget to call parent class initializer
        super(DisseminateResponse, self).__init__()
        self.disseminationResult = disseminationResult




class DisseminationInfo(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    priority = Integer
    SLA = Integer
    dataPolicy = Unicode
    diffusion = Diffusion
    alternativeDiffusion = Diffusion


class DisseminationImplService(ServiceBase):

    __port_types__ = ['DisseminationImplPort']

    @rpc(Unicode, Unicode, DisseminationInfo, _soap_port_type='DisseminationImplPort', _returns=DisseminateResponse)
    def disseminate(self, requestId, fileURI, disseminationInfo):
        print(disseminationInfo.priority, disseminationInfo.SLA)

        status = DisseminationStatus(requestId, 'ONGOING_DISSEMINATION', "mess_hello")
        dissResp = DisseminateResponse(status)


        return dissResp

    @rpc(Unicode, _returns=DisseminateResponse, _soap_port_type='DisseminationImplPort')
    def monitorDissemination(self,requestId):
        
        status = DisseminationStatus(requestId, 'ONGOING_DISSEMINATION', "mess_hello")
        dissResp = DisseminateResponse(status)


        return dissResp

application = Application(
    [DisseminationImplService], 'http://dissemination.harness.openwis.org/',
    name="DisseminationImplService",
    # The input protocol is set as HttpRpc to make our service easy to call.
    # in_protocol=HttpRpc(validator='soft'),
    # out_protocol=JsonDocument(ignore_wrappers=True),
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(validator='lxml')
    )


wsgi_application = WsgiApplication(application)
