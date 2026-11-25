from pathlib import Path

# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# SECURITY AND DEVELOPMENT
# ==========================================

SECRET_KEY = "development-only-replace-before-deployment"

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# ==========================================
# INSTALLED APPLICATIONS
# ==========================================

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "tailwind",
    "theme",
    "django_cotton",
    "apps.dashboard",
]


# ==========================================
# MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==========================================
# URL CONFIGURATION
# ==========================================

ROOT_URLCONF = "config.urls"


# ==========================================
# TEMPLATE CONFIGURATION
# ==========================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ==========================================
# WSGI CONFIGURATION
# ==========================================

WSGI_APPLICATION = "config.wsgi.application"


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

# No database backend configured at this stage.
# Database architecture remains open for future development.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ==========================================
# INTERNATIONALIZATION
# ==========================================

LANGUAGE_CODE = "en-ca"

TIME_ZONE = "America/Toronto"

USE_I18N = True

USE_TZ = True


# ==========================================
# STATIC FILE CONFIGURATION
# ==========================================

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# ==========================================
# MERCHANDISE MEDIA CONFIGURATION
# ==========================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# CSRF token must be accessible to the frontend JavaScript.
CSRF_COOKIE_HTTPONLY = False

# ==========================================
# DEFAULT MODEL CONFIGURATION
# ==========================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==========================================
# TAILWIND CONFIGURATION
# ==========================================

TAILWIND_APP_NAME = "theme"

TAILWIND_USE_STANDALONE_BINARY = True

TAILWIND_STANDALONE_BINARY_VERSION = "v4.3.3"

# ==========================================
# BROWSER SESSION CONFIGURATION
# ==========================================

# SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

SESSION_COOKIE_AGE = 86400
