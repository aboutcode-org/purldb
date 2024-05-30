#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
from unittest import TestCase

import codecs
import json
import ntpath
import os
import posixpath

from django.test import TestCase as DjangoTestCase

from commoncode.resource import VirtualCodebase
from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints
from matchcode_toolkit.fingerprinting import hexstring_to_binarray
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.utils.serializer_helpers import ReturnList
from scancode.cli_test_utils import purl_with_fake_uuid

from matchcode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTestingMixin


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
                       regen=FIXTURES_REGEN, remove_file_date=True):
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
                rd.pop('file_date', None)

            for package_data in rd.get('packages', []):
                # Normalize package_uid
                package_uid = package_data.get('package_uid')
                if package_uid:
                    package_data['package_uid'] = purl_with_fake_uuid(package_uid)

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


class MatchcodeTestCase(CodebaseTester, JsonBasedTestingMixin, BaseTestCase, DjangoTestCase):
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


def _create_virtual_codebase_from_package_resources(package):
    """
    Return a VirtualCodebase from the resources of `package`
    """
    # Create something that looks like a scancode scan so we can import it into
    # a VirtualCodebase
    package_resources = package.resources.order_by('path')
    if not package_resources:
        return

    files = []
    for resource in package_resources:
        files.append(
            {
                'path': resource.path,
                'size': resource.size,
                'sha1': resource.sha1,
                'md5': resource.md5,
                'type': resource.type,
            }
        )

    make_new_root = False
    sample_file_path = files[0].get('path', '')
    root_dir = sample_file_path.split('/')[0]
    for f in files:
        file_path = f.get('path', '')
        if not file_path.startswith(root_dir):
            make_new_root = True
            break

    if make_new_root:
        new_root = '{}-{}'.format(package.name, package.version)
        for f in files:
            new_path = os.path.join(new_root, f.get('path', ''))
            f['path'] = new_path

    # Create VirtualCodebase
    mock_scan = dict(files=files)
    return VirtualCodebase(location=mock_scan)


def index_resource_fingerprints(codebase, package):
    """
    Index fingerprints for directories and resources from `codebase` into the
    ApproximateDirectoryContentIndex, ApproximateDirectoryStructureIndex, and
    ApproximateResourceContentIndex models.

    Return a tuple of integers, `indexed_adci`, `indexed_adsi`, and
    `indexed_arci` that represent the number of indexed
    ApproximateDirectoryContentIndex, ApproximateDirectoryStructureIndex, and
    ApproximateResourceContentIndex created, respectivly.
    """
    from matchcode.models import ApproximateDirectoryContentIndex
    from matchcode.models import ApproximateDirectoryStructureIndex
    from matchcode.models import ApproximateResourceContentIndex

    indexed_adci = 0
    indexed_adsi = 0
    indexed_arci = 0
    for resource in codebase.walk(topdown=False):
        directory_content_fingerprint = resource.extra_data.get('directory_content', '')
        directory_structure_fingerprint = resource.extra_data.get('directory_structure', '')
        resource_content_fingerprint = resource.extra_data.get('halo1', '')

        if directory_content_fingerprint:
            _, adci_created = ApproximateDirectoryContentIndex.index(
                fingerprint=directory_content_fingerprint,
                resource_path=resource.path,
                package=package,
            )
            if adci_created:
                indexed_adci += 1

        if directory_structure_fingerprint:
            _, adsi_created = ApproximateDirectoryStructureIndex.index(
                fingerprint=directory_structure_fingerprint,
                resource_path=resource.path,
                package=package,
            )
            if adsi_created:
                indexed_adsi += 1

        if resource_content_fingerprint:
            _, arci_created = ApproximateResourceContentIndex.index(
                fingerprint=directory_structure_fingerprint,
                resource_path=resource.path,
                package=package,
            )
            if arci_created:
                indexed_arci += 1

    return indexed_adci, indexed_adsi, indexed_arci


def index_package_directories(package):
    """
    Index the directories of `package` to ApproximateDirectoryContentIndex and
    ApproximateDirectoryStructureIndex.

    Return a tuple of integers, `indexed_adci`, `indexed_adsi`, and
    `indexed_arci` that represent the number of indexed
    ApproximateDirectoryContentIndex, ApproximateDirectoryStructureIndex, and
    ApproximateResourceContentIndex created, respectivly.

    Return 0, 0, 0 if a VirtualCodebase cannot be created from the Resources of
    a Package.
    """
    vc = _create_virtual_codebase_from_package_resources(package)
    if not vc:
        return 0, 0, 0

    vc = compute_codebase_directory_fingerprints(vc)
    return index_resource_fingerprints(vc, package)
