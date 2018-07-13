from spyne.application import Application
from spyne.decorator import srpc
from spyne.model.complex import Iterable, ComplexModel
from spyne.model.primitive import Integer, Unicode
# from spyne.protocol.http import HttpRpc
# from spyne.protocol.json import JsonDocument
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase
from spyne.server.wsgi import WsgiApplication

class TestComplex(ComplexModel):

    __namespace__="http://dissemination.harness.openwis.org/"

    var1 = Unicode
    var2 = Unicode


class Dissemination(ServiceBase):
    @srpc(Unicode, Unicode, TestComplex, _returns=Unicode)
    def disseminate(requestId, fileURI, testObject):
        print(testObject.var1, testObject.var2)
        return "{} {}".format(requestId, fileURI)


application = Application(
    [Dissemination], 'http://dissemination.harness.openwis.org/',
    # The input protocol is set as HttpRpc to make our service easy to call.
    # in_protocol=HttpRpc(validator='soft'),
    # out_protocol=JsonDocument(ignore_wrappers=True),
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(validator='lxml')
    )


wsgi_application = WsgiApplication(application)