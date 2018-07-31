from spyne.application import Application
from spyne.decorator import srpc, rpc
from spyne.model.complex import ComplexModel
from lxml import etree

from spyne.interface.wsdl.wsdl11 import Wsdl11, check_method_port, SubElement,WSDL11,WSDL11_SOAP
# from lxml.etree import SubElement
from spyne.model.primitive import Integer, Unicode, Boolean
# from spyne.protocol.http import HttpRpc
# from spyne.protocol.json import JsonDocument
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication

from spyne.const import xml


from spyne.interface.xml_schema._base import XmlSchema

NS_XML = 'http://www.w3.org/XML/1998/namespace'
NS_XSD = 'http://www.w3.org/2001/XMLSchema'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
NS_WSA = 'http://schemas.xmlsoap.org/ws/2003/03/addressing'
NS_XOP = 'http://www.w3.org/2004/08/xop/include'
NS_XHTML = 'http://www.w3.org/1999/xhtml'
NS_PLINK = 'http://schemas.xmlsoap.org/ws/2003/05/partner-link/'
NS_SOAP11_ENC = 'http://schemas.xmlsoap.org/soap/encoding/'
NS_SOAP11_ENV = 'http://schemas.xmlsoap.org/soap/envelope/'
NS_SOAP12_ENC = 'http://www.w3.org/2003/05/soap-encoding'
NS_SOAP12_ENV = 'http://www.w3.org/2003/05/soap-envelope'

NS_WSDL11 = 'http://schemas.xmlsoap.org/wsdl/'
NS_WSDL11_SOAP = 'http://schemas.xmlsoap.org/wsdl/soap/'
NS_WSDL12_SOAP = 'http://schemas.xmlsoap.org/wsdl/soap12/'

NSMAP = {
    'xml': NS_XML,
    'xs': NS_XSD,
    'xsi': NS_XSI,
    'plink': NS_PLINK,
    'soap': NS_WSDL11_SOAP,
    'wsdlsoap12': NS_WSDL12_SOAP,
    'wsdl': NS_WSDL11,
    'soap11enc': NS_SOAP11_ENC,
    'soap11env': NS_SOAP11_ENV,
    'soap12env': NS_SOAP12_ENV,
    'soap12enc': NS_SOAP12_ENC,
    'wsa': NS_WSA,
    'xop': NS_XOP,
}

xml.NSMAP = NSMAP


def _get_binding_name(self, port_type_name):
    if port_type_name == "Dissemination":
        port_type_name = "DisseminationImplServiceSoapBinding"
    return port_type_name # subclasses override to control port names.

Wsdl11._get_binding_name = _get_binding_name

def _add_port_to_service(self, service, port_name, binding_name):
    """ Builds a wsdl:port for a service and binding"""

    pref_tns = self.interface.get_namespace_prefix(self.interface.tns)

    wsdl_port = SubElement(service, WSDL11("port"))
    if port_name == "Dissemination":
        wsdl_port.set('name', "DisseminationImplPort")
    else:
        wsdl_port.set('name', port_name)
    wsdl_port.set('binding', '%s:%s' % (pref_tns, binding_name))

    addr = SubElement(wsdl_port, WSDL11_SOAP("address"))
    addr.set('location', self.url)

Wsdl11._add_port_to_service = _add_port_to_service


def get_schema_node(self, pref):
    """Return schema node for the given namespace prefix."""

    if not (pref in self.schema_dict):
        schema = etree.Element(xml.XSD('schema'),
                                                    nsmap=self.interface.nsmap)

        schema.set("targetNamespace", self.interface.nsmap[pref])
        schema.set("elementFormDefault", "unqualified")
        # schema.set("elementFormDefault", "qualified")

        self.schema_dict[pref] = schema

    else:
        schema = self.schema_dict[pref]

    return schema

XmlSchema.get_schema_node = get_schema_node


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
    # __namespace__="machin"

    # class Attributes(ComplexModel.Attributes):
    #     sub_ns = "machin"


    requestId = Unicode.customize(sub_ns="")
    requestStatus = Unicode(values=['ONGOING_DISSEMINATION', 'DISSEMINATED', 'FAILED']).customize(sub_ns="")
    message = Unicode.customize(sub_ns="")

    def __init__(self,  requestId, requestStatus, message):
        # don't forget to call parent class initializer
        super(DisseminationStatus, self).__init__()
        self.requestId = requestId
        self.requestStatus = requestStatus
        self.message = message 

# class DisseminateResponse(ComplexModel):

#     __namespace__="http://dissemination.harness.openwis.org/"

#     disseminationResult = DisseminationStatus

#     def __init__(self,  disseminationResult):
#         # don't forget to call parent class initializer
#         super(DisseminateResponse, self).__init__()
#         self.disseminationResult = disseminationResult




class DisseminationInfo(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    priority = Integer
    SLA = Integer
    dataPolicy = Unicode
    diffusion = Diffusion
    alternativeDiffusion = Diffusion



class DisseminationImplService(ServiceBase):

    # __service_name__  = "DisseminationImplService"
    __port_types__ = ['Dissemination']
    @rpc(Unicode, Unicode, DisseminationInfo, _port_type='Dissemination', _returns=DisseminationStatus,
    _out_variable_name='disseminationResult')
    def disseminate(ctx, requestId, fileURI, disseminationInfo):
    # @rpc(Unicode, Unicode, DisseminationInfo, _returns=DisseminateResponse)
    # def disseminate(self,requestId, fileURI, disseminationInfo):
    
        print(disseminationInfo.priority, disseminationInfo.SLA)

        status = DisseminationStatus(requestId, 'ONGOING_DISSEMINATION', "mess_hello")
        dissResp = status
        # dissResp.__namespace__= ""
        print(dissResp.__namespace__)
        ctx.descriptor.out_message._type_info['disseminationResult'].Attributes.sub_ns = "truc"
        return dissResp

        

        # test = ctx.function.descriptor.out_message()
        # test.disseminationResult = status
        # test.disseminationResult.__namespace__ = ""
        # print(test.disseminationResult.__namespace__)
        # return test

    @rpc(Unicode, _returns=DisseminationStatus, _port_type='Dissemination', _out_variable_name='disseminationStatus')
    def monitorDissemination(ctx, requestId):
    # @rpc(Unicode, _returns=DisseminateResponse)
    # def monitorDissemination(ctx,requestId):
        
        status = DisseminationStatus(requestId, 'ONGOING_DISSEMINATION', "mess_hello")
        dissResp = status


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

# wsgi_application.doc.wsdl11.interface.classes['disseminateResponse'].__namespace__ = ""

# wsgi_application.doc.wsdl11.build_interface_document("truc")
# wsgi_application.doc.wsdl11.root_elt[0].find('{http://www.w3.org/2001/XMLSchema}schema').attrib['elementFormDefault'] = "unqualified"

print("ok")
