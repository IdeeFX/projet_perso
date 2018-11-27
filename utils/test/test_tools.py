import unittest
from utils.tools import Tools


class TestTools(unittest.TestCase):
    """
    Testing that special characters conversion works properly
    """

    def test_string_conversion(self):

        test = Tools.ack_str("test&")
        self.assertEqual(test, "test&amp;")
        test = Tools.ack_str("test<")
        self.assertEqual(test, "test&lt;")
        test = Tools.ack_str("test>")
        self.assertEqual(test, "test&gt;")
        test = Tools.ack_str("test\'")
        self.assertEqual(test, "test&apos;")
        test = Tools.ack_str("test\"")
        self.assertEqual(test, "test&quot;")

    def test_string_revert_conversion(self):

        test = Tools.ack_decode("test&amp;")
        self.assertEqual(test, "test&" )
        test = Tools.ack_decode("test&lt;")
        self.assertEqual(test, "test<")
        test = Tools.ack_decode("test&gt;")
        self.assertEqual(test,"test>")
        test = Tools.ack_decode("test&apos;")
        self.assertEqual(test, "test\'")
        test = Tools.ack_decode("test&quot;")
        self.assertEqual(test, "test\"")

if __name__ == "__main__":
    unittest.main()