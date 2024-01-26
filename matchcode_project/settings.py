#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from scancodeio.settings import *


INSTALLED_APPS += [
    'clearcode',
    'clearindex',
    'matchcode',
    'minecode',
    'packagedb',
]

# Database

DATABASES = {
    'default': {
        'ENGINE': env.str('SCANCODEIO_DB_ENGINE', 'django.db.backends.postgresql'),
        'HOST': env.str('SCANCODEIO_DB_HOST', 'localhost'),
        'NAME': env.str('SCANCODEIO_DB_NAME', 'matchcodeio'),
        'USER': env.str('SCANCODEIO_DB_USER', 'matchcodeio'),
        'PASSWORD': env.str('SCANCODEIO_DB_PASSWORD', 'matchcodeio'),
        'PORT': env.str('SCANCODEIO_DB_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
    },
    'packagedb': {
        'ENGINE': env.str('PACKAGEDB_DB_ENGINE', 'django.db.backends.postgresql'),
        'HOST': env.str('PACKAGEDB_DB_HOST', 'localhost'),
        'NAME': env.str('PACKAGEDB_DB_NAME', 'packagedb'),
        'USER': env.str('PACKAGEDB_DB_USER', 'packagedb'),
        'PASSWORD': env.str('PACKAGEDB_DB_PASSWORD', 'packagedb'),
        'PORT': env.str('PACKAGEDB_DB_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
    }
}


DATABASE_ROUTERS = [
    'matchcode_project.dbrouter.PackageDBRouter',
    'matchcode_project.dbrouter.ScancodeIORouter',
]

ROOT_URLCONF = 'matchcode_project.urls'
