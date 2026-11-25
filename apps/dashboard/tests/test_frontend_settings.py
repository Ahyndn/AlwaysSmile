from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


class FrontendSettingsTests(SimpleTestCase):
    def test_tailwind_application_is_registered(self):
        self.assertIn(
            "tailwind",
            settings.INSTALLED_APPS,
        )

    def test_theme_application_is_registered(self):
        self.assertIn(
            "theme",
            settings.INSTALLED_APPS,
        )

    def test_tailwind_theme_name_is_configured(self):
        self.assertEqual(
            settings.TAILWIND_APP_NAME,
            "theme",
        )

    def test_standalone_binary_mode_is_enabled(self):
        self.assertTrue(
            settings.TAILWIND_USE_STANDALONE_BINARY,
        )

    def test_tailwind_version_is_configured(self):
        self.assertEqual(
            settings.TAILWIND_STANDALONE_BINARY_VERSION,
            "v4.3.3",
        )

    def test_django_cotton_is_registered(self):
        self.assertIn(
            "django_cotton",
            settings.INSTALLED_APPS,
        )

    def test_theme_application_can_be_loaded(self):
        theme = apps.get_app_config("theme")

        self.assertEqual(
            theme.name,
            "theme",
        )

    def test_dashboard_application_remains_registered(self):
        self.assertIn(
            "apps.dashboard",
            settings.INSTALLED_APPS,
        )
