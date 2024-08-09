#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
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

from minecode.utils_test import JsonBasedTesting


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
