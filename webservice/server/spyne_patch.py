"""
monkey patch because of missing transport tag in wsdl
see https://github.com/arskom/spyne/pull/573
"""

from spyne.interface.wsdl import Wsdl11
from lxml import etree
from lxml.etree import SubElement
from spyne.const.xml import WSDL11, XSD, NS_WSA, WSDL11_SOAP
import spyne.const.xml
from spyne.interface.xml_schema._base import XmlSchema
from spyne.const import xml
PREF_WSA = spyne.const.xml.PREFMAP[NS_WSA]

_in_header_msg_suffix = 'InHeaderMsg'
_out_header_msg_suffix = 'OutHeaderMsg'


# WARNING there is a bug to fix when debugging the code in a IDE:
# see this https://github.com/arskom/spyne/pull/572

# replace odict.__delitem__ by :
    # def __delitem__(self, key):
    #     if not isinstance(key, int):
    #         super(odict, self).__delitem__(key)
    #         key = self.__list.index(key) # ouch.
    #     else:
    #         super(odict, self).__delitem__(self.__list[key])
    #     del self.__list[key]

#see https://github.com/arskom/spyne/pull/573

def add_bindings_for_methods(self, service, root, service_name,
                                    cb_binding):

    pref_tns = self.interface.get_namespace_prefix(self.interface.get_tns())

    def inner(method, binding):
        operation = etree.Element(WSDL11("operation"))
        operation.set('name', method.operation_name)

        soap_operation = SubElement(operation, WSDL11_SOAP("operation"))
        soap_operation.set('soapAction', method.operation_name)
        soap_operation.set('style', 'document')

        # get input
        input = SubElement(operation, WSDL11("input"))
        input.set('name', method.in_message.get_element_name())

        soap_body = SubElement(input, WSDL11_SOAP("body"))
        soap_body.set('use', 'literal')

        # get input soap header
        in_header = method.in_header
        if in_header is None:
            in_header = service.__in_header__

        if not (in_header is None):
            if isinstance(in_header, (list, tuple)):
                in_headers = in_header
            else:
                in_headers = (in_header,)

            if len(in_headers) > 1:
                in_header_message_name = ''.join((method.name,
                                                    _in_header_msg_suffix))
            else:
                in_header_message_name = in_headers[0].get_type_name()

            for header in in_headers:
                soap_header = SubElement(input, WSDL11_SOAP('header'))
                soap_header.set('use', 'literal')
                soap_header.set('message', '%s:%s' % (
                            header.get_namespace_prefix(self.interface),
                            in_header_message_name))
                soap_header.set('part', header.get_type_name())

        if not (method.is_async or method.is_callback):
            output = SubElement(operation, WSDL11("output"))
            output.set('name', method.out_message.get_element_name())

            soap_body = SubElement(output, WSDL11_SOAP("body"))
            soap_body.set('use', 'literal')

            # get output soap header
            out_header = method.out_header
            if out_header is None:
                out_header = service.__out_header__

            if not (out_header is None):
                if isinstance(out_header, (list, tuple)):
                    out_headers = out_header
                else:
                    out_headers = (out_header,)

                if len(out_headers) > 1:
                    out_header_message_name = ''.join((method.name,
                                                    _out_header_msg_suffix))
                else:
                    out_header_message_name = out_headers[0].get_type_name()

                for header in out_headers:
                    soap_header = SubElement(output, WSDL11_SOAP("header"))
                    soap_header.set('use', 'literal')
                    soap_header.set('message', '%s:%s' % (
                            header.get_namespace_prefix(self.interface),
                            out_header_message_name))
                    soap_header.set('part', header.get_type_name())

            if not (method.faults is None):
                for f in method.faults:
                    wsdl_fault = SubElement(operation, WSDL11("fault"))
                    wsdl_fault.set('name', f.get_type_name())

                    soap_fault = SubElement(wsdl_fault, WSDL11_SOAP("fault"))
                    soap_fault.set('name', f.get_type_name())
                    soap_fault.set('use', 'literal')

        if method.is_callback:
            relates_to = SubElement(input, WSDL11_SOAP("header"))

            relates_to.set('message', '%s:RelatesToHeader' % pref_tns)
            relates_to.set('part', 'RelatesTo')
            relates_to.set('use', 'literal')

            cb_binding.append(operation)

        else:
            if method.is_async:
                rt_header = SubElement(input, WSDL11_SOAP("header"))
                rt_header.set('message', '%s:ReplyToHeader' % pref_tns)
                rt_header.set('part', 'ReplyTo')
                rt_header.set('use', 'literal')

                mid_header = SubElement(input, WSDL11_SOAP("header"))
                mid_header.set('message', '%s:MessageIDHeader' % pref_tns)
                mid_header.set('part', 'MessageID')
                mid_header.set('use', 'literal')

            binding.append(operation)

    port_type_list = service.get_port_types()
    if len(port_type_list) > 0:
        for port_type_name in port_type_list:

            # create binding nodes
            binding = SubElement(root, WSDL11("binding"))
            binding.set('name', port_type_name)
            binding.set('type', '%s:%s'% (pref_tns, port_type_name))

            transport = SubElement(binding, WSDL11_SOAP("binding"))
            transport.set('style', 'document')
            transport.set('transport', self.interface.app.transport)

            for m in service.public_methods.values():
                if m.port_type == port_type_name:
                    inner(m, binding)

    else:
        # here is the default port.
        if cb_binding is None:
            cb_binding = SubElement(root, WSDL11("binding"))
            cb_binding.set('name', service_name)
            cb_binding.set('type', '%s:%s'% (pref_tns, service_name))

            transport = SubElement(cb_binding, WSDL11_SOAP("binding"))
            transport.set('style', 'document')
            transport.set('transport', self.interface.app.transport)

        for m in service.public_methods.values():
            inner(m, cb_binding)

    return cb_binding

def _add_callbacks(self, service, root, types, service_name, url):
    ns_tns = self.interface.get_tns()
    pref_tns = 'tns'

    cb_port_type = None

    # add necessary async headers
    # WS-Addressing -> RelatesTo ReplyTo MessageID
    # callback porttype
    if service._has_callbacks():
        wsa_schema = SubElement(types, XSD("schema"))
        wsa_schema.set("targetNamespace", '%sCallback'  % ns_tns)
        wsa_schema.set("elementFormDefault", "qualified")

        import_ = SubElement(wsa_schema, XSD("import"))
        import_.set("namespace", NS_WSA)
        import_.set("schemaLocation", NS_WSA)

        relt_message = SubElement(root, WSDL11("message"))
        relt_message.set('name', 'RelatesToHeader')
        relt_part = SubElement(relt_message, WSDL11("part"))
        relt_part.set('name', 'RelatesTo')
        relt_part.set('element', '%s:RelatesTo' % PREF_WSA)

        reply_message = SubElement(root, WSDL11("message"))
        reply_message.set('name', 'ReplyToHeader')
        reply_part = SubElement(reply_message, WSDL11("part"))
        reply_part.set('name', 'ReplyTo')
        reply_part.set('element', '%s:ReplyTo' % PREF_WSA)

        id_header = SubElement(root, WSDL11("message"))
        id_header.set('name', 'MessageIDHeader')
        id_part = SubElement(id_header, WSDL11("part"))
        id_part.set('name', 'MessageID')
        id_part.set('element', '%s:MessageID' % PREF_WSA)

        # make portTypes
        cb_port_type = SubElement(root, WSDL11("portType"))
        cb_port_type.set('name', '%sCallback' % service_name)

        cb_service_name = '%sCallback' % service_name

        cb_service = SubElement(root, WSDL11("service"))
        cb_service.set('name', cb_service_name)

        cb_wsdl_port = SubElement(cb_service, WSDL11("port"))
        cb_wsdl_port.set('name', cb_service_name)
        cb_wsdl_port.set('binding', '%s:%s' % (pref_tns, cb_service_name))

        cb_address = SubElement(cb_wsdl_port, WSDL11_SOAP("address"))
        cb_address.set('location', url)

    return cb_port_type




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

# XmlSchema.get_schema_node = get_schema_node
Wsdl11.add_bindings_for_methods = add_bindings_for_methods
# Wsdl11._add_port_to_service = _add_port_to_service