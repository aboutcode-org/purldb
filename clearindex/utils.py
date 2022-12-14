#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from unittest import TestCase
import logging
import ntpath
import os
import posixpath
import traceback

from django.core.management.base import BaseCommand
from django.test import TestCase as DjangoTestCase

from discovery.utils_test import JsonBasedTesting


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


"""
The conventions used for the tests are:
- for tests that require files these are stored in the testfiles directory
- each test must use its own sub directory in testfiles. The is called the
'base'
- testfiles that are more than a few KB should be in a bzip2 tarball
"""


class BaseTestCase(TestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')

    @classmethod
    def get_test_loc(cls, path):
        """
        Given a path relative to the test files directory, return the location
        to a test file or directory for this path. No copy is done.
        """
        path = to_os_native_path(path)
        location = os.path.abspath(os.path.join(cls.BASE_DIR, path))
        return location


class ClearIndexTestCase(JsonBasedTesting, BaseTestCase, DjangoTestCase):
    databases = '__all__'


def to_os_native_path(path):
    """
    Normalize a path to use the native OS path separator.
    """
    path = path.replace(posixpath.sep, os.path.sep)
    path = path.replace(ntpath.sep, os.path.sep)
    path = path.rstrip(os.path.sep)
    return path
