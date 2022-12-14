#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import json
import os

from django.test import TestCase as DjangoTestCase

from mock import MagicMock
from mock import Mock
from mock import patch

from packagedb.models import Package

from discovery.utils_test import mocked_requests_get
from discovery.utils_test import JsonBasedTesting

from discovery import mappers
from discovery import visitors
from discovery.visitors import URI
from discovery.models import ResourceURI
from discovery.route import Router
from discovery.management.commands.run_map import map_uri


class TestPypiVisit(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    '''
import unittest
import xmlrpc
from mock import patch

class TestFoo(unittest.TestCase):
    """
    A simple test
    """
    @patch('xmlrpc.server')
    def test_first(self, mock_xmlrpc):
        m = mock_xmlrpc.return_value
        m.multiply.return_value = 6
        server = xmlrpc.server("http://kushaldas.in/")
        res = server.multiply(2, 3)
        self.assertEqual(res, 6)
'''
    @patch('xmlrpc.client.ServerProxy')
    def test_PypiIndexVisitor(self, mock_serverproxyclass):
        package_list = ["0",
                        "0-._.-._.-._.-._.-._.-._.-0",
                        "0.0.1",
                        "00print_lol",
                        "vmnet",
                        "vmo",
                        "vmock",
                        "vmonere",
                        "VMPC", ]
        instance = mock_serverproxyclass.return_value
        instance.list_packages.return_value = iter(package_list)
        uri = 'https://pypi.python.org/pypi/'
        uris, _data, _error = visitors.pypi.PypiIndexVisitor(uri)
        self.assertIsNone(_data)

        expected_loc = self.get_test_loc('pypi/pypiindexvisitor-expected.json')
        self.check_expected_uris(uris, expected_loc)

    def test_PypiPackageVisitor(self):
        uri = 'https://pypi.python.org/pypi/CAGE/json'
        test_loc = self.get_test_loc('pypi/cage.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _error = visitors.pypi.PypiPackageVisitor(uri)

        expected_loc = self.get_test_loc('pypi/expected_uris-cage.json')
        self.check_expected_uris(uris, expected_loc)

    def test_PypiPackageVisitor_2(self):
        uri = 'https://pypi.python.org/pypi/boolean.py/json'
        test_loc = self.get_test_loc('pypi/boolean.py.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = visitors.pypi.PypiPackageVisitor(uri)

        expected_loc = self.get_test_loc('pypi/expected_uris-boolean.py.json')
        self.check_expected_uris(uris, expected_loc)

    def test_PypiPackageReleaseVisitor_cage12(self):
        uri = 'https://pypi.python.org/pypi/CAGE/1.1.2/json'
        test_loc = self.get_test_loc('pypi/cage_1.1.2.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _error = visitors.pypi.PypiPackageReleaseVisitor(uri)

        expected_loc = self.get_test_loc('pypi/expected_uris-cage_1.1.2.json')
        self.check_expected_uris(uris, expected_loc)

        expected_loc = self.get_test_loc('pypi/expected_data-cage_1.1.2.json')
        self.check_expected_results(data, expected_loc)

    def test_PypiPackageReleaseVisitor_cage13(self):
        uri = 'https://pypi.python.org/pypi/CAGE/1.1.3/json'
        test_loc = self.get_test_loc('pypi/cage_1.1.3.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _error = visitors.pypi.PypiPackageReleaseVisitor(uri)

        expected_loc = self.get_test_loc('pypi/expected_uris-cage_1.1.3.json')
        self.check_expected_uris(uris, expected_loc)

        expected_loc = self.get_test_loc('pypi/expected_data-cage_1.1.3.json')
        self.check_expected_results(data, expected_loc)

    def test_PypiPackageReleaseVisitor_boolean(self):
        uri = 'https://pypi.python.org/pypi/boolean.py/2.0.dev3/json'
        test_loc = self.get_test_loc('pypi/boolean.py-2.0.dev3.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _error = visitors.pypi.PypiPackageReleaseVisitor(uri)

        expected_loc = self.get_test_loc('pypi/expected_uris-boolean.py-2.0.dev3.json')
        self.check_expected_uris(uris, expected_loc)

        expected_loc = self.get_test_loc('pypi/expected_data-boolean.py-2.0.dev3.json')
        self.check_expected_results(data, expected_loc)


class MockResourceURI(object):

    def __init__(self, uri, data):
        self.uri = uri
        self.data = data
        self.package_url = None


class TestPypiMap(JsonBasedTesting, DjangoTestCase):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_packages_lxml(self):
        with open(self.get_test_loc('pypi/lxml-3.2.0.json')) as pypi_meta:
            metadata = json.load(pypi_meta)
        packages = mappers.pypi.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/expected-lxml-3.2.0.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages_boolean(self):
        with open(self.get_test_loc('pypi/boolean.py-2.0.dev3.json')) as pypi_meta:
            metadata = json.load(pypi_meta)
        packages = mappers.pypi.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/expected-boolean.py-2.0.dev3.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages_cage13(self):
        with open(self.get_test_loc('pypi/cage_1.1.3.json')) as pypi_meta:
            metadata = json.load(pypi_meta)
        packages = mappers.pypi.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/expected-CAGE-1.1.3.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_packages_cage12(self):
        with open(self.get_test_loc('pypi/cage_1.1.2.json')) as pypi_meta:
            metadata = json.load(pypi_meta)
        packages = mappers.pypi.build_packages(metadata)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/expected-CAGE-1.1.2.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_PypiPackageMapper_cage(self):
        data = open(self.get_test_loc('pypi/cage_1.1.2.json')).read()
        uri = 'https://pypi.python.org/pypi/CAGE/1.1.2/json'
        resuri = MockResourceURI(uri, data)
        packages = mappers.pypi.PypiPackageMapper(uri, resuri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/expected-CAGE-1.1.2.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_PypiPackageMapper_lxml(self):
        data = open(self.get_test_loc('pypi/lxml-3.2.0.json')).read()
        uri = 'https://pypi.python.org/pypi/lxml/3.2.0/json'
        resuri = MockResourceURI(uri, data)
        packages = mappers.pypi.PypiPackageMapper(uri, resuri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/expected-lxml-3.2.0.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_pypi_map(self):
        # setup: add a mappable URI
        with open(self.get_test_loc('pypi/map/3to2-1.1.1.json')) as mappable:
            resuri = ResourceURI(**json.load(mappable))
            resuri.save()

        # sanity check
        packages = mappers.pypi.PypiPackageMapper(resuri.uri, resuri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('pypi/map/expected-3to2-1.1.1.json')
        self.check_expected_results(packages, expected_loc, regen=False)

        # build a mock router
        router = Router()
        router.append('https://pypi.python.org/pypi/3to2/1.1.1/json', mappers.pypi.PypiPackageMapper)

        # sanity check
        expected_mapped_package_uri = 'https://pypi.python.org/packages/8f/ab/58a363eca982c40e9ee5a7ca439e8ffc5243dde2ae660ba1ffdd4868026b/3to2-1.1.1.zip'
        self.assertEqual(0, Package.objects.filter(download_url=expected_mapped_package_uri).count())

        # test proper
        map_uri(resuri, _map_router=router)
        mapped = Package.objects.filter(download_url=expected_mapped_package_uri)
        self.assertEqual(1, mapped.count())
