from zeep import Client
from collections import namedtuple

# test = namedtuple('test', 'var1')

# testSent = test("machin")

# print(testSent)

# class TestClient():

#     def __init__(self, var1,var2):
#         self.var1 = var1
#         self.var2 = var2

# testSent = TestClient("machin","truc")


client = Client('http://localhost:5000/soap?wsdl')


factory = client.type_factory('http://dissemination.harness.openwis.org/')
info = factory.DisseminationInfo(priority=5,SLA=6,dataPolicy="truc")
# testSent = factory.TestComplex(var1='John',var2=5)
result = client.service.disseminate(requestId="Dave", fileURI="truc", disseminationInfo=info)
# print(result)
print("fin")
# node = client.create_message(client.service, 'disseminate', requestId="Dave", fileURI="truc")
# print(node)