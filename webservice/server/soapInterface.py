import logging
import socket
import os
from spyne.application import Application
from spyne.decorator import rpc
from spyne.model.complex import ComplexModel
from spyne.model.primitive import Integer, Unicode, Boolean
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication
from notification_receiver.receiver import Notification
from utils.database import Database
from utils.const import PORT


# TODO move those class definitions in another file
MailDispatchMode = Unicode(values=['TO', 'CC', 'BCC'])
MailAttachmentMode = Unicode(values=['EMBEDDED_IN_BODY', 'AS_ATTACHMENT'])
requestStatus = Unicode(
    values=['ONGOING_DISSEMINATION', 'DISSEMINATED', 'FAILED'])

LOGGER = logging.getLogger(__name__)

class Diffusion(ComplexModel):

    __namespace__ = "http://dissemination.harness.openwis.org/"

    fileName = Unicode


class FTPDiffusion(Diffusion):

    class Attributes(Diffusion.Attributes):
        exc_interface = True

    __namespace__ = "http://dissemination.harness.openwis.org/"

    host = Unicode
    port = Unicode
    user = Unicode
    password = Unicode
    passive = Boolean
    remotePath = Unicode
    checkFileSize = Boolean
    encrypted = Boolean


class MailDiffusion(Diffusion):

    __namespace__ = "http://dissemination.harness.openwis.org/"

    address = Unicode
    headerLine = Unicode
    subject = Unicode
    dispatchMode = Unicode(values=['TO', 'CC', 'BCC'])
    attachmentMode = Unicode(values=['EMBEDDED_IN_BODY', 'AS_ATTACHMENT'])


class DisseminationStatus(ComplexModel):

    __namespace__ = "http://dissemination.harness.openwis.org/"

    requestId = Unicode.customize(sub_ns="")
    requestStatus = Unicode(
        values=['ONGOING_DISSEMINATION', 'DISSEMINATED', 'FAILED']).customize(sub_ns="")
    message = Unicode.customize(sub_ns="")

    def __init__(self,  requestId, requestStatus, message):

        super(DisseminationStatus, self).__init__()
        self.requestId = requestId
        self.requestStatus = requestStatus
        self.message = message


class DisseminationInfo(ComplexModel):

    __namespace__ = "http://dissemination.harness.openwis.org/"

    priority = Integer
    SLA = Integer
    dataPolicy = Unicode
    diffusion = Diffusion
    alternativeDiffusion = Diffusion


class DisseminationImplService(ServiceBase):

    __port_types__ = ['Dissemination']

    @rpc(Unicode, Unicode, DisseminationInfo, _soap_port_type='Dissemination', _returns=DisseminationStatus,
         _out_variable_name='disseminationResult')
    def disseminate(ctx, requestId, fileURI, disseminationInfo):
        # modify the namespace to comply with openwis client service
        ctx.descriptor.out_message._type_info['disseminationResult'].Attributes.sub_ns = ""

        try:
            client_ip = ctx.transport.req["HTTP_X_REAL_IP"]
        except KeyError:
            client_ip = ctx.transport.req.get("REMOTE_ADDR")
        LOGGER.debug("Received request from ip %s", client_ip)
        notif = Notification(requestId, fileURI, disseminationInfo, client_ip)
        request_status = notif.process()
        diss_resp = DisseminationStatus(requestId, request_status, "dissemination request received")

        return diss_resp

    @rpc(Unicode, _returns=DisseminationStatus, _soap_port_type='Dissemination', _out_variable_name='disseminationStatus')
    def monitorDissemination(ctx, requestId):
        # modify the namespace to comply with openwis client service
        ctx.descriptor.out_message._type_info['disseminationStatus'].Attributes.sub_ns = ""

        status, message = Database.get_diss_status(requestId)

        diss_resp = DisseminationStatus(requestId, status, message)
        return diss_resp


application = Application(
    [DisseminationImplService], 'http://dissemination.harness.openwis.org/',
    name="DisseminationImplService",
    in_protocol=Soap11(),
    out_protocol=Soap11()
)



wsgi_application = WsgiApplication(application)
# TODO url to set with variable env
port = os.environ.get("MFSERV_NGINX_PORT") or PORT
hostname = socket.gethostname()
url = ("http://{hostname}.meteo.fr:{port}/"
       "harnais-diss-v2/webservice/"
       "Dissemination?wsdl".format(hostname=hostname,
                                  port=port))
url = os.environ.get("MFSERV_HARNESS_SOAP_ADRESS") or url
wsgi_application.doc.wsdl11.build_interface_document(url)
