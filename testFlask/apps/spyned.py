from spyne.application import Application
from spyne.decorator import srpc, rpc
from spyne.model.complex import ComplexModel

from spyne.interface.wsdl.wsdl11 import Wsdl11, check_method_port, SubElement,WSDL11
# from lxml.etree import SubElement
from spyne.model.primitive import Integer, Unicode, Boolean
# from spyne.protocol.http import HttpRpc
# from spyne.protocol.json import JsonDocument
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication


def _get_binding_name(self, port_type_name):
    if port_type_name == "DisseminationImplPort":
        port_type_name = "DisseminationImplServiceSoapBinding"
    return port_type_name # subclasses override to control port names.

Wsdl11._get_binding_name = _get_binding_name


def add_port_type(self, service, root, service_name, types, url):
        # FIXME: I don't think this call is working.
        cb_port_type = self._add_callbacks(service, root, types,
                                                              service_name, url)
        applied_service_name = self._get_applied_service_name(service)

        port_binding_names = []
        port_type_list = service.get_port_types()
        if len(port_type_list) > 0:
            for port_type_name in port_type_list:
                port_type = self._get_or_create_port_type(port_type_name)
                if port_type_name == "DisseminationImplPort":
                    port_type.set('name', "Dissemination")
                else:
                    port_type.set('name', port_type_name)

                binding_name = self._get_binding_name(port_type_name)
                port_binding_names.append((port_type_name, binding_name))

        else:
            port_type = self._get_or_create_port_type(service_name)
            port_type.set('name', service_name)

            binding_name = self._get_binding_name(service_name)
            port_binding_names.append((service_name, binding_name))

        for method in service.public_methods.values():
            check_method_port(service, method)

            if method.is_callback:
                operation = SubElement(cb_port_type, WSDL11("operation"))
            else:
                operation = SubElement(port_type, WSDL11("operation"))

            operation.set('name', method.operation_name)

            if method.doc is not None:
                operation.append(E(WSDL11("documentation"), method.doc))

            operation.set('parameterOrder', method.in_message.get_element_name())

            op_input = SubElement(operation, WSDL11("input"))
            op_input.set('name', method.in_message.get_element_name())
            op_input.set('message',
                          method.in_message.get_element_name_ns(self.interface))

            if (not method.is_callback) and (not method.is_async):
                op_output = SubElement(operation, WSDL11("output"))
                op_output.set('name', method.out_message.get_element_name())
                op_output.set('message', method.out_message.get_element_name_ns(
                                                                self.interface))

                if not (method.faults is None):
                    for f in method.faults:
                        fault = SubElement(operation, WSDL11("fault"))
                        fault.set('name', f.get_type_name())
                        fault.set('message', '%s:%s' % (
                                        f.get_namespace_prefix(self.interface),
                                        f.get_type_name()))

        ser = self.service_elt_dict[applied_service_name]
        for port_name, binding_name in port_binding_names:
            self._add_port_to_service(ser, port_name, binding_name)


Wsdl11.add_port_type = add_port_type

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

    # __service_name__  = "DisseminationImplService"
    __port_types__ = ['DisseminationImplPort']
    @srpc(Unicode, Unicode, DisseminationInfo, _port_type='DisseminationImplPort', _returns=DisseminateResponse)
    def disseminate(requestId, fileURI, disseminationInfo):
    # @rpc(Unicode, Unicode, DisseminationInfo, _returns=DisseminateResponse)
    # def disseminate(self,requestId, fileURI, disseminationInfo):
    
        print(disseminationInfo.priority, disseminationInfo.SLA)

        status = DisseminationStatus(requestId, 'ONGOING_DISSEMINATION', "mess_hello")
        dissResp = DisseminateResponse(status)


        return dissResp

    # @srpc(Unicode, _returns=DisseminateResponse, _soap_port_type='DisseminationImplPort')
    # def monitorDissemination(requestId):
    # # @rpc(Unicode, _returns=DisseminateResponse)
    # # def monitorDissemination(ctx,requestId):
        
    #     status = DisseminationStatus(requestId, 'ONGOING_DISSEMINATION', "mess_hello")
    #     dissResp = DisseminateResponse(status)


    #     return dissResp

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

print("ok")
