import unittest

from hython.phonetics import pronounce_identifier


class PhoneticsTests(unittest.TestCase):
    def test_snake_case(self):
        self.assertEqual(pronounce_identifier("hello_world"), "흐에르르오_우오르르드")

    def test_camel_case_is_separated(self):
        self.assertIn("_", pronounce_identifier("HTTPError"))

