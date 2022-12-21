#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from unittest import TestCase

import json
import ntpath
import os
import posixpath

from django.test import TestCase as DjangoTestCase

from commoncode.resource import VirtualCodebase

from matchcode.fingerprinting import hexstring_to_binarray


############## TEST UTILITIES ##############
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


class CodebaseTester(object):
    def check_codebase(self, codebase, expected_codebase_json_loc,
                       regen=False, remove_file_date=True):
        """
        Check the Resources of the `codebase` Codebase objects are the same
        as the data in the `expected_codebase_json_loc` JSON file location,

        If `regen` is True the expected_file WILL BE overwritten with the `codebase`
        data. This is convenient for updating tests expectations. But use with
        caution.

        if `remove_file_date` is True, the file.date attribute is removed.
        """

        def serializer(r):
            rd = r.to_dict(with_info=True)
            if remove_file_date:
                rd.pop('file_data', None)
            return rd

        results = list(map(serializer, codebase.walk(topdown=True)))
        if regen:
            with open(expected_codebase_json_loc, 'w') as reg:
                json.dump(dict(files=results), reg, indent=2, separators=(',', ': '))

        expected_vc = VirtualCodebase(location=expected_codebase_json_loc)
        expected = list(map(serializer, expected_vc.walk(topdown=True)))

        # NOTE we redump the JSON as a string for a more efficient display of the
        # failures comparison/diff
        expected = json.dumps(expected, indent=2, separators=(',', ': '))
        results = json.dumps(results, indent=2, separators=(',', ': '))
        self.assertEqual(expected, results)


class MatchcodeTestCase(CodebaseTester, BaseTestCase, DjangoTestCase):
    databases = '__all__'


def to_os_native_path(path):
    """
    Normalize a path to use the native OS path separator.
    """
    path = path.replace(posixpath.sep, os.path.sep)
    path = path.replace(ntpath.sep, os.path.sep)
    path = path.rstrip(os.path.sep)
    return path


def load_resources_from_scan(scan_location, package):
    from packagedb.models import Resource
    vc = VirtualCodebase(
        location=scan_location,
    )
    for resource in vc.walk(topdown=True):
        created_resource, _ = Resource.objects.get_or_create(
            package=package,
            path=resource.path,
            size=resource.size,
            sha1=resource.sha1,
            md5=resource.md5,
            is_file=resource.type == 'file'
        )


def index_packages_sha1():
    """
    Reindex all the packages for exact sha1 matching.
    """
    from matchcode.models import ExactPackageArchiveIndex
    from packagedb.models import Package

    for package in Package.objects.filter(sha1__isnull=False):
        sha1_in_bin = hexstring_to_binarray(package.sha1)
        _ = ExactPackageArchiveIndex.objects.create(
            package=package,
            sha1=sha1_in_bin
        )


def index_package_files_sha1(package, scan_location):
    """
    Index for SHA1 the package files found in the JSON scan at scan_location
    """
    from matchcode.models import ExactFileIndex

    resource_attributes = dict()
    vc = VirtualCodebase(
        location=scan_location,
        resource_attributes=resource_attributes
    )

    for resource in vc.walk(topdown=True):
        sha1 = resource.sha1
        if not sha1:
            continue
        sha1_in_bin = hexstring_to_binarray(sha1)
        package_file, created = ExactFileIndex.objects.get_or_create(
            sha1=sha1_in_bin,
            package=package,
        )
