# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
#
# ClearCode is a free software tool from nexB Inc. and others.
# Visit https://github.com/nexB/clearcode-toolkit/ for support and download.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Django Settings for ClearCode DB.
"""

DATABASES = dict(
    default=dict(
        ENGINE='django.db.backends.postgresql',
        HOST='localhost',
        PORT='5432',
        NAME='packagedb',
        USER='packagedb',
        PASSWORD='packagedb',
        ATOMIC_REQUESTS=True,
    )
)

# TODO: Add some sort of api auth if you expose to the world
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

ROOT_URLCONF = 'clearcode.api'

# To disable running migration on each run, enable a fake migration below
# class FakeMigrations(dict):
#     """
#     Fake migration class to avoid running migrations at all. For the CLI
#     usage, a new DB is created on each run, so running migrations has no value.
#     inspired by https://github.com/henriquebastos/django-test-without-migrations
#     """
#     def __getitem__(self, item):
#         return 'do not run any migrations'
#
#     def __contains__(self, item):
#         return True
# MIGRATION_MODULES = dbconf.FakeMigrations()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'clearcode',
    'rest_framework',
]

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

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
        }
    }
]

# SECURITY WARNING: keep the secret key used in a production webapp!
# here we are running a local CLI-only application and do not need a Django secret
SECRET_KEY = '# SECURITY WARNING: keep the secret key used in a production webapp!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
TIME_ZONE = 'UTC'

STATIC_URL = '/static/'

