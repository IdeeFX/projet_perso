from spyne.application import Application
from spyne.decorator import srpc
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


class Diffusion(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    fileName = Unicode

class FTPDiffusion(Diffusion):

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
    dispatchMode = MailDispatchMode
    attachmentMode = MailAttachmentMode


class DisseminationStatus(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    requestId = Unicode
    requestStatus = requestStatus
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


class DisseminationService(ServiceBase):
    @srpc(Unicode, Unicode, DisseminationInfo, _returns=DisseminateResponse)
    def disseminate(requestId, fileURI, testObject):
        print(testObject.priority, testObject.SLA)

        status = DisseminationStatus("reqId_1234", 'ONGOING_DISSEMINATION', "mess_hello")
        dissResp = DisseminateResponse(status)


        return dissResp


application = Application(
    [DisseminationService], 'http://dissemination.harness.openwis.org/',
    # The input protocol is set as HttpRpc to make our service easy to call.
    # in_protocol=HttpRpc(validator='soft'),
    # out_protocol=JsonDocument(ignore_wrappers=True),
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(validator='lxml')
    )


wsgi_application = WsgiApplication(application)
