#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os
from os.path import join, dirname, abspath

"""
Django settings for minecodeio project.
"""


here = lambda *dirs: join(abspath(dirname(__file__)), *dirs)
BASE_DIR = here('..', '..')
root = lambda *dirs: join(abspath(BASE_DIR), *dirs)
root_parent = lambda *dirs: join(abspath(root('..')), *dirs)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'discovery',
    'packagedb',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'minecodeio.urls'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'packagedb',
        'USER': 'packagedb',
        'PASSWORD': 'packagedb',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        'ATOMIC_REQUESTS': True,
    },
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'packagedb.api_custom.PageSizePagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.AdminRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ),
}

# Internationalization

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Pacific'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            # The cached template loader is a class-based loader that you
            # configure with a list of other loaders that it should wrap.
            # The wrapped loaders are used to locate unknown templates when
            # they are first encountered. The cached loader then stores the
            # compiled Template in memory. The cached Template instance is
            # returned for subsequent requests to load the same template.
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]

# Cache

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Security

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SECURE = True

# Requests

REQUESTS_ARGS = {

    # Configuration for Request to use Tor over a Privoxy proxy
    # Comment-out for a direct access
    # 'proxies': {
    #     'http': 'http://127.0.0.1:8118',
    #     'https': 'https://127.0.0.1:8118',
    # }
}

# Instead of sending out real emails the console backend just writes the emails
# that would be sent to the standard output.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Active seeders: each active seeder class need to be added explictly here
ACTIVE_SEEDERS = [
    'discovery.visitors.npm.NpmSeed',
]
