import unittest

from app.languages import TRANSLATIONS, get_text


class TestLanguages(unittest.TestCase):
    def test_get_text_happy_path_en(self):
        self.assertEqual(get_text("en", "page_title_setup"), TRANSLATIONS["en"]["page_title_setup"])

    def test_get_text_happy_path_tr(self):
        self.assertEqual(get_text("tr", "page_title_setup"), TRANSLATIONS["tr"]["page_title_setup"])

    def test_get_text_happy_path_de(self):
        self.assertEqual(get_text("de", "page_title_setup"), TRANSLATIONS["de"]["page_title_setup"])

    def test_get_text_fallback_unsupported_language(self):
        self.assertEqual(get_text("fr", "page_title_setup"), TRANSLATIONS["en"]["page_title_setup"])

    def test_get_text_missing_key(self):
        self.assertEqual(get_text("en", "non_existent_key_12345"), "[non_existent_key_12345]")

    def test_get_text_missing_key_unsupported_language(self):
        self.assertEqual(get_text("fr", "non_existent_key_12345"), "[non_existent_key_12345]")

    def test_get_text_empty_language(self):
        self.assertEqual(get_text("", "page_title_setup"), TRANSLATIONS["en"]["page_title_setup"])

    def test_get_text_none_language(self):
        self.assertEqual(get_text(None, "page_title_setup"), TRANSLATIONS["en"]["page_title_setup"])

    def test_get_text_empty_key(self):
        self.assertEqual(get_text("en", ""), "[]")


if __name__ == "__main__":
    unittest.main()
