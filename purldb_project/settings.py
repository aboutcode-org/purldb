#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import sys
from pathlib import Path

import environ

from purldb_project import __version__

PURLDB_VERSION = __version__

PROJECT_DIR = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_DIR.parent


# Environment

ENV_FILE = "/etc/purldb/.env"
if not Path(ENV_FILE).exists():
    ENV_FILE = ROOT_DIR / ".env"

env = environ.Env()
environ.Env.read_env(str(ENV_FILE))

# Security

SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[".localhost", "127.0.0.1", "[::1]"])

# SECURITY WARNING: do not run with debug turned on in production
DEBUG = env.bool("PURLDB_DEBUG", default=False)

PURLDB_REQUIRE_AUTHENTICATION = env.bool("PURLDB_REQUIRE_AUTHENTICATION", default=False)

# SECURITY WARNING: do not  run with debug turned on in production
DEBUG_TOOLBAR = env.bool("PURLDB_DEBUG_TOOLBAR", default=False)

PURLDB_PASSWORD_MIN_LENGTH = env.int("PURLDB_PASSWORD_MIN_LENGTH", default=14)

# SCANCODE.IO
SCANCODEIO_URL = env.str("SCANCODEIO_URL", "")
SCANCODEIO_API_KEY = env.str("SCANCODEIO_API_KEY", "")

# PurlDB

PURLDB_LOG_LEVEL = env.str("PURLDB_LOG_LEVEL", "INFO")

SITE_URL = env.str("SITE_URL", default="")

# Application definition

INSTALLED_APPS = (
    # Local apps
    # Must come before Third-party apps for proper templates override
    "clearcode",
    "clearindex",
    "minecode",
    "matchcode",
    "packagedb",
    # Django built-in
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.humanize",
    # Third-party apps
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "rest_framework.authtoken",
    "django_rq",
)

MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "purldb_project.urls"

WSGI_APPLICATION = "purldb_project.wsgi.application"

SECURE_PROXY_SSL_HEADER = env.tuple(
    "SECURE_PROXY_SSL_HEADER", default=("HTTP_X_FORWARDED_PROTO", "https")
)

# API

DATA_UPLOAD_MAX_NUMBER_FIELDS = env.int("DATA_UPLOAD_MAX_NUMBER_FIELDS", default=2048)

# Database
DATABASES = {
    "default": {
        "ENGINE": env.str("PACKAGEDB_DB_ENGINE", "django.db.backends.postgresql"),
        "HOST": env.str("PACKAGEDB_DB_HOST", "localhost"),
        "NAME": env.str("PACKAGEDB_DB_NAME", "packagedb"),
        "USER": env.str("PACKAGEDB_DB_USER", "packagedb"),
        "PASSWORD": env.str("PACKAGEDB_DB_PASSWORD", "packagedb"),
        "PORT": env.str("PACKAGEDB_DB_PORT", "5432"),
        "ATOMIC_REQUESTS": True,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(PROJECT_DIR.joinpath("templates"))],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
            ],
        },
    },
]

# Login

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Passwords

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": PURLDB_PASSWORD_MIN_LENGTH,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Testing

# True if running tests through `./manage test or pytest`
IS_TESTS = any(clue in arg for arg in sys.argv for clue in ("test", "pytest"))

# Cache

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default",
    }
}

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "scanpipe": {
            "handlers": ["null"] if IS_TESTS else ["console"],
            "level": PURLDB_LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["null"] if IS_TESTS else ["console"],
            "propagate": False,
        },
        # Set PURLDB_LOG_LEVEL=DEBUG to display all SQL queries in the console.
        "django.db.backends": {
            "level": PURLDB_LOG_LEVEL,
        },
    },
}

# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = env.str("TIME_ZONE", default="UTC")

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"

STATIC_ROOT = "/var/purldb/static/"

STATICFILES_DIRS = [
    PROJECT_DIR / "static",
]

# Third-party apps

# Django restframework

REST_FRAMEWORK_DEFAULT_THROTTLE_RATES = {"anon": "3600/hour", "user": "10800/hour"}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.TokenAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.AdminRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "packagedb.throttling.StaffUserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": REST_FRAMEWORK_DEFAULT_THROTTLE_RATES,
    "EXCEPTION_HANDLER": "packagedb.throttling.throttled_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "packagedb.api_custom.PageSizePagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Limit the load on the Database returning a small number of records by default. https://github.com/aboutcode-org/vulnerablecode/issues/819
    "PAGE_SIZE": 20,
}

if not PURLDB_REQUIRE_AUTHENTICATION:
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = ("rest_framework.permissions.AllowAny",)

if DEBUG_TOOLBAR:
    INSTALLED_APPS += ("debug_toolbar",)

    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

    DEBUG_TOOLBAR_PANELS = (
        "debug_toolbar.panels.history.HistoryPanel",
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
    )

    INTERNAL_IPS = [
        "127.0.0.1",
    ]

# Active seeders: each active seeder class need to be added explicitly here
ACTIVE_SEEDERS = [
    "minecode.miners.maven.MavenSeed",
]

SPECTACULAR_SETTINGS = {
    "TITLE": "PurlDB API",
    "DESCRIPTION": "Tools to create and expose a database of purls (Package URLs)",
    "VERSION": PURLDB_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
}

RQ_QUEUES = {
    "default": {
        "HOST": env.str("PURLDB_REDIS_HOST", default="localhost"),
        "PORT": env.str("PURLDB_REDIS_PORT", default="6379"),
        "DB": env.int("PURLDB_REDIS_DB", default=0),
        "USERNAME": env.str("PURLDB_REDIS_USERNAME", default=None),
        "PASSWORD": env.str("PURLDB_REDIS_PASSWORD", default=""),
        "DEFAULT_TIMEOUT": env.int("PURLDB_REDIS_DEFAULT_TIMEOUT", default=360),
        # Enable SSL for Redis connections when deploying purldb in environments
        # where Redis is hosted on a separate system (e.g., cloud deployment or remote
        # Redis server) to secure data in transit.
        "SSL": env.bool("PURLDB_REDIS_SSL", default=False)
    }
}

PURLDB_ASYNC = env.bool("PURLDB_ASYNC", default=False)
if not PURLDB_ASYNC:
    for queue_config in RQ_QUEUES.values():
        queue_config["ASYNC"] = False

# FederatedCode integration

FEDERATEDCODE_HOST_URL = env.str("FEDERATEDCODE_HOST_URL", default="")
FEDERATEDCODE_PURLDB_REMOTE_USERNAME = env.str(
    "FEDERATEDCODE_PURLDB_REMOTE_USERNAME", default="purldb"
)
