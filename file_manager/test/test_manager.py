import unittest
import tempfile
import getpass
import os
from settings.settings_manager import SettingsManager
from file_manager.manager import ConnectionPointer
from utils.setup_tree import HarnessTree
from utils.log_setup import setup_logging


# class TestScp(unittest.TestCase):

#     def setUp(self):

#         SettingsManager.setter(
#             "harnaisLogdir", tempfile.gettempdir(), testing=True)
#         setup_logging()
#         self.temp_dir = tempfile.TemporaryDirectory()
#         self.pwd = os.getenv("$TEST_SCP_PASSWORD")

#     def test_scp(self):

#         # TODO prepare for automation
#         SettingsManager.update(dict(openwisStagingPath="/tmp/",
#                                     openwisHost="localhost",
#                                     # openwisHost="wisauth-int-p",
#                                     openwisSftpUser=os.getenv("$USER"),
#                                     # openwisSftpUser="openwis",
#                                     openwisSftpPassword= self.pwd or getpass.getpass()
#                                     ),
#                                testing=True)

#         # HarnessTree.setter("temp_dissRequest_B", self.temp_dir, testing=True)
#         HarnessTree.setter("temp_dissRequest_B", "/tmp/", testing=True)

#         pointer = ConnectionPointer("123456","localhost")

#         with tempfile.NamedTemporaryFile() as test_file:
#             # pointer.scp(test_file.name)
#             pointer.scp_dir("/tmp/", "/tmp/")

#             # dirname = self.temp_dir.name
#             # basename = os.path.basename(test_file.name)
#             dirname = "/tmp/"
#             basename = "test.txt"
#             self.assertTrue(os.path.isfile(os.path.join(dirname, basename)),
#                             msg="Failure to scp a dummy file from {h}".format(h=SettingsManager.get("openwisHost")))
#             # self.assertTrue(os.path.isfile(os.path.join(dirname,basename)),
#             #                 msg="Failure to scp a dummy file from localhost to localhost")

#     def tearDown(self):

#         self.temp_dir.cleanup()


# if __name__ == "__main__":
#     unittest.main()
