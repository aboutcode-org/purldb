#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from os.path import join, dirname, abspath

"""
Django settings for local development
"""

# Using exec() instead of "import *" to avoid any side effects
with open(join(dirname(abspath(__file__)), 'base.py')) as f:
    exec(f.read())


DEBUG = True
TEMPLATES[0]['OPTIONS']['debug'] = True

SECRET_KEY = '-@j@p68cdzzk2s3x8=i#*ml#@-k3$l=b7_cd440$36pn)msdam'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
