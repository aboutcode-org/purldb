#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
from django.core.wsgi import get_wsgi_application


"""
WSGI config for packagedbio project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'packagedbio.settings.production')

application = get_wsgi_application()
