"""
Enterprise HRMS (demo) - Django settings.

All secrets come from environment variables or a local `.env` file (see
`.env.example`). With no `.env` the app runs in development mode on SQLite,
so it can be tried in a few minutes without PostgreSQL.
"""
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
SECRET_KEY = config("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is False.")
    SECRET_KEY = "dev-only-insecure-key-change-me"

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "masters",
    "employees",
    "housing",
    "duties",
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIST],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database --------------------------------------------------------------
DB_ENGINE = config("HRMS_DB_ENGINE", default="sqlite")
if DB_ENGINE == "postgres":
    DB_PASSWORD = config("HRMS_DB_PASSWORD", default="")
    if not DB_PASSWORD:
        raise ImproperlyConfigured("HRMS_DB_PASSWORD must be set when using PostgreSQL.")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("HRMS_DB_NAME", default="hrms_demo"),
            "USER": config("HRMS_DB_USER", default="postgres"),
            "PASSWORD": DB_PASSWORD,
            "HOST": config("HRMS_DB_HOST", default="127.0.0.1"),
            "PORT": config("HRMS_DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = config("HRMS_TIME_ZONE", default="Asia/Karachi")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [FRONTEND_DIST / "assets"] if (FRONTEND_DIST / "assets").exists() else []
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["accounts.permissions.RoleBasedPermission"],
    "DEFAULT_PAGINATION_CLASS": None,
}

CSRF_TRUSTED_ORIGINS = config(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default="http://127.0.0.1:8888,http://localhost:8888,http://127.0.0.1:5444,http://localhost:5444",
    cast=Csv(),
)

HRMS_ORG_NAME = config("HRMS_ORG_NAME", default="NexGen Holdings Ltd.")
HRMS_CURRENCY = config("HRMS_CURRENCY", default="Rs")

if not DEBUG:
    SESSION_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = "DENY"
