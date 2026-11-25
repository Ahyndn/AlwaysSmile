from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


class ProjectSettingsTests(SimpleTestCase):
    def test_dashboard_application_is_registered(self):
        self.assertIn(
            "apps.dashboard",
            settings.INSTALLED_APPS,
        )

    def test_database_is_configured(self):
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"],
            "django.db.backends.sqlite3",
        )

    def test_authentication_application_is_not_installed(self):
        self.assertNotIn(
            "django.contrib.auth",
            settings.INSTALLED_APPS,
        )

    def test_template_directory_is_configured(self):
        template_config = settings.TEMPLATES[0]

        self.assertIn(
            settings.BASE_DIR / "templates",
            template_config["DIRS"],
        )

    def test_application_templates_are_enabled(self):

        template_config = settings.TEMPLATES[0]

        # Django's standard template configuration
        # uses APP_DIRS=True.

        if "APP_DIRS" in template_config:
            self.assertTrue(
                template_config["APP_DIRS"],
            )

        else:
            # Django Cotton configures custom template
            # loaders, including application templates.

            loaders = template_config.get("OPTIONS", {}).get("loaders", [])

            self.assertIn(
                "django.template.loaders.app_directories.Loader",
                str(loaders),
            )

    def test_static_directory_is_configured(self):
        self.assertIn(
            settings.BASE_DIR / "static",
            settings.STATICFILES_DIRS,
        )

    def test_csrf_protection_is_enabled(self):
        self.assertIn(
            "django.middleware.csrf.CsrfViewMiddleware",
            settings.MIDDLEWARE,
        )

    def test_dashboard_application_verbose_name(self):
        dashboard = apps.get_app_config("dashboard")

        self.assertEqual(
            dashboard.verbose_name,
            "AlwaysSmile",
        )

    def test_session_application_is_installed(self):
        self.assertIn(
            "django.contrib.sessions",
            settings.INSTALLED_APPS,
        )

    def test_session_middleware_is_enabled(self):
        self.assertIn(
            "django.contrib.sessions.middleware.SessionMiddleware",
            settings.MIDDLEWARE,
        )
