#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import codecs
import json
import ntpath
import os
import posixpath
import shutil
import stat
import tarfile
from collections import OrderedDict
from itertools import chain
from unittest import TestCase

from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase as DjangoTestCase

from commoncode.testcase import FileBasedTesting
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.utils.serializer_helpers import ReturnList
from scancode.cli_test_utils import purl_with_fake_uuid

from minecode.tests import FIXTURES_REGEN
from minecode.utils import get_temp_dir

"""
The conventions used for the tests are:
- for tests that require files these are stored in the testfiles directory
- tests that create temp files should clean up after themselves. Subclass
MiningTestCase and call self.to_clean(path_to_clean) to have this done for you
automatically
- each test must use its own sub directory in testfiles. The is called the
'base'
- testfiles that are more than a few KB should be in a bzip2 tarball
"""


class BaseMiningTestCase(TestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), "testfiles")

    def setUp(self):
        if not hasattr(self, "to_delete"):
            self.to_delete = []

    def tearDown(self):
        for pth in getattr(self, "to_delete", []):
            self.make_rwe(pth)
            shutil.rmtree(pth, ignore_errors=True)

    def make_path_read_write(self, location):
        try:
            # u+rwx g+rx
            os.chmod(location, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        except OSError:
            pass

    def make_rwe(self, location):
        """
        Make all the files in path user and group readable, writable and
        executable, if possible.
        """
        if not os.path.exists(location):
            return
        if not os.path.isdir(location):
            self.make_path_read_write(location)
            return
        for pth, dirs, files in os.walk(location):
            for d in dirs:
                self.make_path_read_write(os.path.join(pth, d))
            for f in files:
                self.make_path_read_write(os.path.join(pth, f))

    def extract_archive(self, location, delete=True):
        """
        Extract a tar.bz2 archive located at path.
        Return the temporary dir where the trace was extracted.
        The temporary dir is deleted once tests are completed.
        """
        with open(location, "rb") as input_tar:
            tar = tarfile.open(fileobj=input_tar)
            extract_dir = self.get_temp_dir(delete)
            tar.extractall(extract_dir)
            self.make_rwe(extract_dir)
            return extract_dir

    def build_archive(self, real_location, tar_path, outarch):
        from contextlib import closing

        with closing(tarfile.open(outarch, mode="w:bz2")) as out:
            out.add(real_location, arcname=tar_path)

    def get_temp_dir(self, delete=True):
        assert dir and dir != ""
        tmp_dir = get_temp_dir(base_dir="", prefix="minecode-tests-")
        if delete:
            self.to_delete.append(tmp_dir)
        return tmp_dir

    def copy_test_dir(self, test_path):
        """
        Given a directory path relative to test files, make a copy of the
        directory in a temporary test area and return the path to this
        directory. Some filtering is done, such as ignoring version control
        metafile folders and files.
        """
        test_path = self.get_test_loc(test_path)
        test_path = to_os_native_path(test_path)
        # do no create the target dir, but only its parent
        parent = os.path.dirname(test_path)
        if parent:
            prepared_dir = self.get_temp_dir(parent)
        else:
            prepared_dir = self.get_temp_dir()
        # the last segment of target dir does not exist yet copytree needs a
        # non existing target
        target_dir = os.path.basename(test_path)
        target_dir = os.path.join(prepared_dir, target_dir)

        origin_dir = self.get_test_loc(test_path)
        shutil.copytree(origin_dir, target_dir, symlinks=None)
        # finally some cleanup of VCS and similar
        remove_vcs(target_dir)
        return target_dir

    @classmethod
    def get_test_loc(cls, path):
        """
        Given a path relative to the test files directory, return the location
        to a test file or directory for this path. No copy is done.
        """
        path = to_os_native_path(path)
        location = os.path.abspath(os.path.join(cls.BASE_DIR, path))
        return location


class MiningTestCase(BaseMiningTestCase, DjangoTestCase):
    pass


def remove_vcs(location):
    """Remove well known version control directories."""
    for root, dirs, _files in os.walk(location):
        for vcs_dir in "CVS", ".svn", ".git", ".hg":
            if vcs_dir in dirs:
                shutil.rmtree(os.path.join(root, vcs_dir), False)


def to_os_native_path(path):
    """Normalize a path to use the native OS path separator."""
    path = path.replace(posixpath.sep, os.path.sep)
    path = path.replace(ntpath.sep, os.path.sep)
    path = path.rstrip(os.path.sep)
    return path


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


def mocked_requests_get(url, location):
    """
    Return a MockResponse object by parsing the content of
    the file at `location` in a response to request to a single `url`.
    """
    with open(location, "rb") as loc:
        return MockResponse(loc.read(), 200)


def mocked_requests_get_for_uris(url_to_location, *args, **kwargs):
    """
    Return a MockResponse object by parsing the content of
    the file at `location` in a response to request to `url` based on a
    mapping of url->location.
    """
    location = url_to_location[args[0]]
    with open(location, "rb") as loc:
        return MockResponse(loc.read(), 200)


def response_403(url, request):
    """Return a HTTP response with status 403."""
    return {"status_code": 403, "content": ""}


class JsonBasedTestingMixin(TestCase):
    def _normalize_results(self, data, fields_to_remove=[]):
        """
        Return `data`, where any `package_uid` value has been normalized with
        `purl_with_fake_uuid()` and fields from `fields_to_remove` have been
        removed from it.
        """
        if type(data) in (list, ReturnList):
            return [self._normalize_results(entry, fields_to_remove) for entry in data]

        if type(data) in (dict, OrderedDict, ReturnDict):
            normalized_data = {}
            for key, value in data.items():
                if type(value) in (list, ReturnList, dict, OrderedDict, ReturnDict):
                    value = self._normalize_results(value, fields_to_remove)
                if (
                    key in ("package_uid", "dependency_uid", "for_package_uid")
                    and value
                ):
                    value = purl_with_fake_uuid(value)
                if key == "for_packages":
                    value = [purl_with_fake_uuid(package_uid) for package_uid in value]
                if key in fields_to_remove:
                    continue
                normalized_data[key] = value
            return normalized_data

        return data

    def _remove_fields_from_results(self, data, fields_to_remove):
        if type(data) in (list, ReturnList):
            return [
                self._remove_fields_from_results(entry, fields_to_remove)
                for entry in data
            ]

        if type(data) in (dict, OrderedDict, ReturnDict):
            # Remove fields from results and normalize Package UIDs
            for field in fields_to_remove:
                if field not in data:
                    continue
                data.pop(field)

    def check_expected_results(
        self, results, expected_loc, fields_to_remove=[], regen=FIXTURES_REGEN
    ):
        """
        Check `results` are  equal to expected data stored in a JSON
        file at `expected_loc`.
        `results` can be a JSON string or a regular Python structure.

        Regen the expected JSON if `regen` is True.
        """
        if isinstance(results, str):
            results = json.loads(results)

        results = self._normalize_results(results, fields_to_remove)

        if regen:
            with codecs.open(expected_loc, mode="wb", encoding="utf-8") as expect:
                json.dump(results, expect, indent=2, separators=(",", ":"))

        with codecs.open(expected_loc, mode="rb", encoding="utf-8") as expect:
            expected = json.load(expect)

        results = json.loads(json.dumps(results))
        self.assertEqual(expected, results)


class JsonBasedTesting(JsonBasedTestingMixin, FileBasedTesting):
    def _normalize_results(self, data, fields_to_remove=[]):
        """
        Return the `data`, where any `package_uid` value has been normalized
        with `purl_with_fake_uuid()` and fields from `fields_to_remove` that
        have been removed from `data`.
        """
        if type(data) in (list, ReturnList):
            return [self._normalize_results(entry, fields_to_remove) for entry in data]

        if type(data) in (dict, OrderedDict, ReturnDict):
            normalized_data = {}
            for key, value in data.items():
                if type(value) in (list, ReturnList, dict, OrderedDict, ReturnDict):
                    value = self._normalize_results(value, fields_to_remove)
                if (
                    key in ("package_uid", "dependency_uid", "for_package_uid")
                    and value
                ):
                    value = purl_with_fake_uuid(value)
                if key == "for_packages":
                    value = [purl_with_fake_uuid(package_uid) for package_uid in value]
                if key in fields_to_remove:
                    continue
                normalized_data[key] = value
            return normalized_data

        return data

    def _remove_fields_from_results(self, data, fields_to_remove):
        if type(data) in (list, ReturnList):
            return [
                self._remove_fields_from_results(entry, fields_to_remove)
                for entry in data
            ]

        if type(data) in (dict, OrderedDict, ReturnDict):
            # Remove fields from results and normalize Package UIDs
            for field in fields_to_remove:
                if field not in data:
                    continue
                data.pop(field)

    def check_expected_uris(
        self, uris, expected_loc, data_is_json=False, regen=FIXTURES_REGEN
    ):
        """
        Check a `uris` iterable of URIs matches the data stored in the JSON file
        at `expected_loc`.
        """
        results = []
        for uri in uris:
            uri_dict = uri.to_dict(data_is_json=data_is_json)
            if uri_dict.get("date"):
                # Parse date since date will be used as Date field in
                # ResourceURI object, to make it as string format is just for
                # test comparation.
                # FIXME: we should ONLY have strings there!!!
                uri_dict["date"] = str(uri_dict.get("date"))
            results.append(uri_dict)
        self.check_expected_results(
            results=results, expected_loc=expected_loc, regen=regen
        )


def model_to_dict(instance, fields=None, exclude=None):
    """
    Return a mapping containing the data in ``instance``.

    ``fields`` is an optional list of field names. If provided, only the
    named fields will be included in the returned dict.

    ``exclude`` is an optional list of field names. If provided, the
    named fields will be excluded from the returned dict, even if they
    are listed in the ``fields`` argument.

    Note that all field with the word "date" in their name is converted
    to a boolean value to abstract test results from dates.

    Copied from django.forms.models. model_to_dict
    license: bsd-new
    see ABOUT file for details
    """
    opts = instance._meta
    data = dict()
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if not getattr(f, "editable", False):
            continue
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        value = f.value_from_object(instance)
        if "date" in f.name:
            value = bool(value)
        data[f.name] = value
    return data


class TestMigrations(DjangoTestCase):
    @property
    def app(self):
        return apps.get_containing_app_config(self.app_name).name

    app_name = None
    migrate_from = None
    migrate_to = None

    def setUp(self):
        assert (
            self.migrate_from and self.migrate_to
        ), f"TestCase '{type(self).__name__}' must define migrate_from and migrate_to properties"
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # # Reverse to the original migration
        executor.migrate(self.migrate_from)

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload.
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        pass
