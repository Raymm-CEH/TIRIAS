import unittest

from tirias.app_registry import get_application, list_applications


class TestApplicationRegistry(unittest.TestCase):

    def test_approved_applications_exist(self):
        self.assertIsNotNone(get_application("firefox"))
        self.assertIsNotNone(get_application("mousepad"))
        self.assertIsNotNone(get_application("thunar"))

    def test_unknown_application_is_rejected(self):
        self.assertIsNone(get_application("unknown_app"))

    def test_application_names_are_normalized(self):
        self.assertIsNotNone(get_application(" FIREFOX "))

    def test_registry_contains_five_apps(self):
        self.assertEqual(len(list_applications()), 5)


if __name__ == "__main__":
    unittest.main()
