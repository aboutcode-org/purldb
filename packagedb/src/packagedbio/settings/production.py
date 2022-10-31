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
Django settings for production
"""


# Using exec() instead of "import *" to avoid any side effects
with open(join(dirname(abspath(__file__)), 'base.py')) as f:
    exec(f.read())


def get_secret(setting):
    """
    Gets the secret variable or return explicit exceptions.
    """
    import json
    from django.core.exceptions import ImproperlyConfigured

    with open('/home/packagedb/.secrets.json') as f:
        secrets = json.loads(f.read())

    try:
        return secrets[setting]
    except KeyError:
        error_msg = 'Set the {} environment variable'.format(setting)
        raise ImproperlyConfigured(error_msg)


SECRET_KEY = get_secret('SECRET_KEY')

ADMINS = (
    ('Thomas', 'tdruez@nexb.com'),
    ('Philippe', 'pombredanne@nexb.com'),
    ('infra', 'infra@nexb.com'),
)

MANAGERS = ADMINS

ALLOWED_HOSTS = ['.packagedb.io']

WSGI_APPLICATION = 'packagedb.wsgi.application'

STATIC_ROOT = '/var/www/packagedb/static/'

STATIC_URL = '/static/'

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'scanner.tasks': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}
