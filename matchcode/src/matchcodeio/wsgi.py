#
# Copyright (c) nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

import os
from django.core.wsgi import get_wsgi_application


"""
WSGI config for matchcodeio project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchcodeio.settings')

application = get_wsgi_application()
