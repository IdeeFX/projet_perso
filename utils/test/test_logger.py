import unittest
from utils.log_setup import setup_logging

class TestLogging(unittest.TestCase):

    def setUp(self):
        pass

    def test_find_default_config(self):
        try:
            setup_logging()
            config_found = True
        except FileNotFoundError:
            config_found = False
        self.assertTrue(config_found)

    def test_cant_find_default_config(self):
        wrong_path = "/imaginarydirectory/ImaginaryLoggerFileConfig.yaml"
        self.assertRaises(FileNotFoundError, setup_logging, default_path=wrong_path)

    #TODO : test to check that config is ok

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
