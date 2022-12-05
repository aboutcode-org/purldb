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

import django
from django.apps import apps
from django.conf import settings

from clearcode import dbsettings


"""
Configuration helpers for the embedded sqlite DB used through Django's ORM.
You must call configure() before calling or importing anything else from ScanCode.

WARNING: DO NOT USE THESE IF YOU WANT TO USE SCANCODE IN A REGULAR DJANGO WEB APP.
THE SETTINGS DEFINED HERE ARE ONLY FOR USING SCANCODE AS A COMMAND LINE OR WHEN USING
SCANCODE AS A LIBRARY OUTSIDE OF A DJANGO WEB APPLICATION.
"""


def configure(settings_module=dbsettings, verbose=False):
    """
    Configure minimally Django (in particular the ORM and DB) using the
    `settings_modules` module. When using as a library you must call this
    function at least once before calling other code.
    """
    if not settings.configured:
        settings.configure(**get_settings(settings_module))
    # call django.setup() only once
    if not apps.ready:
        django.setup()
    create_db(verbose=verbose)


def get_settings(settings_module=dbsettings):
    """
    Return a mapping of UPPERCASE settings from a module
    """
    # settings are all UPPERCASE
    sets = [s for s in dir(dbsettings) if s.isupper()]
    return {s: getattr(dbsettings, s) for s in sets}


def create_db(verbose=False, _already_created=[]):
    """
    Create the database by invoking the migrate command behind the scenes.
    """
    if not _already_created:
        verbosity = 2 if verbose else 0
        from django.core.management import call_command
        call_command('migrate', verbosity=verbosity, interactive=False, run_syncdb=True)
        _already_created.append(True)
