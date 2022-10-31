#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
from os import getenv
import traceback

from django.conf import settings
from django.core.management.base import BaseCommand


class VerboseCommand(BaseCommand):
    """
    Base verbosity-aware Command.
    Command modules should define logging and subclasses should call
       logger.setLevel(self.get_verbosity(**options))
    in their handle() method.
    """

    def get_verbosity(self, **options):
        verbosity = int(options.get('verbosity', 1))
        levels = {1: logging.INFO, 2: logging.ERROR, 3: logging.DEBUG}
        return levels.get(verbosity, logging.CRITICAL)

    MUST_STOP = False

    @classmethod
    def stop_handler(cls, *args, **kwargs):
        """
        Signal handler use to support a graceful exit when flag is to True.
        Subclasses must create this signal to use this:
            signal.signal(signal.SIGTERM, Command.stop_handler)
        """
        cls.MUST_STOP = True


def get_error_message(e):
    """
    Return an error message with a traceback given an exception.
    """
    tb = traceback.format_exc()
    msg = e.__class__.__name__ + ' ' + repr(e)
    msg += '\n' + tb
    return msg


def get_settings(var_name):
    """
    Return the settings value from the environment or Django settings.
    """
    return getenv(var_name) or getattr(settings, var_name, None) or ''
