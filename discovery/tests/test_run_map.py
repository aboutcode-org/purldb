#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import os
from io import StringIO

from django.core import management
from django.utils import timezone

from packagedcode.models import Package as ScannedPackage

import packagedb

from discovery.utils_test import MiningTestCase

from discovery.management.commands.run_map import map_uri
from discovery.management.commands.run_map import merge_packages
from discovery.models import ResourceURI
from discovery.route import Router
from discovery.models import ScannableURI
from discovery.utils_test import JsonBasedTesting


class RunMapTest(JsonBasedTesting, MiningTestCase):
    BASE_DIR = os.path.join(os.path.dirname(__file__), 'testfiles')
    maxDiff = None

    def test_map_uri(self):
        # setup
        # build a mock mapper and register it in a router
        uri = 'http://testdomap.com'

        def mock_mapper(uri, resource_uri):
            return [ScannedPackage(
                type='maven',
                namespace='org.apache.spark',
                name='spark-streaming_2.10',
                version='1.2.0',
                qualifiers=dict(extension='pom'),
                download_url='http://testdomap.com',
                sha1='beef'
            )]

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri,
            last_visit_date=timezone.now(),
            package_url='pkg:maven/org.apache.spark/spark-streaming_2.10@1.2.0?extension=pom')
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we are clear of Package before
        before = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, before.count())

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(1, mapped.count())
        self.assertEqual('pkg:maven/org.apache.spark/spark-streaming_2.10@1.2.0?extension=pom', mapped[0].package_url)

        # test history
        history = mapped[0].get_history()
        self.assertIsNotNone(history)
        self.assertEqual('New Package created from ResourceURI: {} via map_uri().'.format(uri), history[0].get('message'))

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)

        # check that a ScannableURI has been created
        scannable = ScannableURI.objects.filter(uri='http://testdomap.com')
        self.assertEqual(1, scannable.count())

    def test_map_uri_continues_after_raised_exception(self):
        # setup
        # build a mock mapper and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_mapper(uri, resource_uri):
            raise Exception()

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri, last_visit_date=timezone.now())
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we are clear of Package before
        before = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, before.count())

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, mapped.count())

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)
        self.assertTrue(resource_uri.map_error is not None)

        # check that a ScannableURI has not been created
        scannable = ScannableURI.objects.filter(uri='http://testdomap.com')
        self.assertEqual(0, scannable.count())

    def test_map_uri_continues_if_unknown_type_in_package_iterator(self):
        # setup
        # build a mock mapper and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_mapper(uri, resource_uri):
            return ['some string']

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri, last_visit_date=timezone.now())
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we are clear of Package before
        before = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, before.count())

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, mapped.count())

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)
        self.assertTrue('Not a ScanCode PackageData type' in resource_uri.map_error)

        # check that a ScannableURI has not been created
        scannable = ScannableURI.objects.filter(uri='http://testdomap.com')
        self.assertEqual(0, scannable.count())

    def test_map_uri_continues_if_no_download_url_in_package_iterator(self):
        # setup
        # build a mock mapper and register it in a router
        uri = 'http://nexb_visit.com'

        class MP(ScannedPackage):
            pass

        def mock_mapper(uri, resource_uri):
            return [
                MP(type='generic', name='foo', sha1='beef')
            ]

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri, last_visit_date=timezone.now())
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we are clear of Package before
        before = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, before.count())

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, mapped.count())

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)
        self.assertTrue('No download_url for package' in resource_uri.map_error)

        # check that a ScannableURI has not been created
        scannable = ScannableURI.objects.filter(uri='http://testdomap.com')
        self.assertEqual(0, scannable.count())

    def test_map_uri_continues_after_raised_exception_in_package_iterator(self):
        # setup
        # build a mock mapper and register it in a router
        uri = 'http://nexb_visit.com'

        class MP(ScannedPackage):

            def to_dict(self, **kwargs):
                raise Exception('ScannedPackage issue')

            def __getattribute__(self, item):
                raise Exception('ScannedPackage issue')
                return ScannedPackage.__getattribute__(self, item)

        def mock_mapper(uri, resource_uri):
            return [
                MP(type='generic', name='foo', download_url=uri, sha1='beef')
            ]

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri, last_visit_date=timezone.now())
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we are clear of Package before
        before = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, before.count())

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(
            download_url='http://testdomap.com')
        self.assertEqual(0, mapped.count())

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)
        self.assertTrue('ScannedPackage issue' in resource_uri.map_error)
        self.assertTrue('Failed to map while' in resource_uri.map_error)

        # check that a ScannableURI has not been created
        scannable = ScannableURI.objects.filter(uri='http://testdomap.com')
        self.assertEqual(0, scannable.count())

    def test_map_uri_with_no_route_defined_does_not_map(self):
        # setup
        # build a mock mapper and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_mapper(uri, resource_uri):
            return [
                ScannedPackage(
                    uri='http://test.com',
                    type='generic',
                    name='testpack',
                )
            ]

        router = Router()
        router.append('http://nexb.com', mock_mapper)
        resource_uri = ResourceURI.objects.create(uri=uri)

        # test proper
        map_uri(resource_uri, _map_router=router)
        try:
            ResourceURI.objects.get(uri='http://test.com')
            self.fail('URI should not have been created')
        except ResourceURI.DoesNotExist:
            pass

    def test_run_map_command(self):
        output = StringIO()
        management.call_command('run_map', exit_on_empty=True, stdout=output)
        self.assertEquals('', output.getvalue())

    def test_map_uri_does_update_with_same_mining_level(self):
        # setup
        # build a mock mapper and register it in a router
        download_url = 'http://testdomap2.com'
        new_p = ScannedPackage(
            type='generic',
            name='pack',
            version='0.2',
            description='Description Updated',
            download_url=download_url
        )

        uri = 'http://testdomap2.com'

        def mock_mapper(uri, resource_uri):
            return [new_p]

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri,
            last_visit_date=timezone.now(),
            mining_level=0
        )
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we have an existing Package before
        packagedb.models.Package.objects.insert(
            mining_level=0,
            type='generic',
            name='pack',
            version='0.1',
            description='Description Existing',
            download_url=download_url,
            sha1='beef',
        )

        # test proper
        map_uri(resource_uri, _map_router=router)

        mapped = packagedb.models.Package.objects.filter(download_url=download_url)
        self.assertEqual(1, mapped.count())

        # test history
        history = mapped[0].get_history()
        self.assertIsNotNone(history)
        self.assertEqual('Existing Package values replaced due to ResourceURI mining level via map_uri().'.format(uri), history[0].get('message'))

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)

        # check that the Package has been updated correctly
        expected_loc = self.get_test_loc('run_map/test_map_uri_does_update_with_same_mining_level-expected.json')
        result = mapped[0].to_dict()
        self.check_expected_results(result, expected_loc, regen=False)

        # Since we manually insert a Package without using `map_uri`, a
        # ScannableURI should not have been created. An update to a package
        # by `map_uri` should also not create a ScannableURI
        scannable = ScannableURI.objects.all()
        self.assertEqual(0, scannable.count())

    def test_map_uri_update_only_empties_with_lesser_new_mining_level(self):
        # setup
        # build a mock mapper and register it in a router
        download_url = 'http://testdomap3.com'
        new_p = ScannedPackage(
            type='generic',
            name='pack',
            version='0.2',
            description='Description Updated',
            download_url=download_url,
            sha1='feed'
        )

        uri = 'http://nexb_visit.com'

        def mock_mapper(uri, resource_uri):
            return [new_p]

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri,
            last_visit_date=timezone.now(),
            mining_level=0
        )
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we have an existing Package before
        packagedb.models.Package.objects.insert(
            # NOTE: existing is 10, new is 0
            mining_level=10,
            type='generic',
            name='pack',
            version='0.1',
            description='',
            download_url=download_url,
            sha1='',
        )

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(download_url=download_url)
        self.assertEqual(1, mapped.count())

        # test history
        history = mapped[0].get_history()
        self.assertIsNotNone(history)
        self.assertEqual('Existing Package values retained due to ResourceURI mining level via map_uri().'.format(uri), history[0].get('message'))

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)

        # check that the Package has been updated correctly
        expected_loc = self.get_test_loc('run_map/test_map_uri_update_only_empties_with_lesser_new_mining_level-expected.json')
        result = mapped[0].to_dict()
        self.check_expected_results(result, expected_loc, regen=False)

        # Since we manually insert a Package without using `map_uri`, a
        # ScannableURI should not have been created. An update to a package
        # by `map_uri` should also not create a ScannableURI
        scannable = ScannableURI.objects.all()
        self.assertEqual(0, scannable.count())

    def test_map_uri_replace_with_new_with_higher_new_mining_level(self):
        # setup
        # build a mock mapper and register it in a router
        download_url = 'http://testdomap4.com'
        new_p = ScannedPackage(
            type='generic',
            name='pack2',
            version='0.2',
            description='Description Updated',
            download_url=download_url
        )

        uri = 'http://nexb_visit.com'

        def mock_mapper(uri, resource_uri):
            return [new_p]

        router = Router()
        router.append(uri, mock_mapper)

        resolved = router.resolve(uri)
        assert resolved == mock_mapper

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(
            uri=uri,
            last_visit_date=timezone.now(),
            mining_level=10
        )
        assert ResourceURI.objects.get(uri=uri) == resource_uri
        resource_uri.is_mappable = True
        resource_uri.save()

        # ensure that we have an existing Package before
        packagedb.models.Package.objects.insert(
            # NOTE: existing is 5, new is 10
            mining_level=5,
            name='pack',
            version='0.1',
            description='',
            download_url=download_url,
            type='generic',
            sha1='beef',
        )

        # test proper
        map_uri(resource_uri, _map_router=router)
        mapped = packagedb.models.Package.objects.filter(download_url=download_url)
        self.assertEqual(1, mapped.count())

        # test history
        history = mapped[0].get_history()
        self.assertIsNotNone(history)
        self.assertEqual('Existing Package values replaced due to ResourceURI mining level via map_uri().'.format(uri), history[0].get('message'))

        # check that the ResourceURI status has been updated correctly
        resource_uri = ResourceURI.objects.get(uri=uri)
        self.assertEqual(None, resource_uri.wip_date)
        self.assertFalse(resource_uri.last_map_date is None)

        # check that the Package has been updated correctly
        expected_loc = self.get_test_loc('run_map/test_map_uri_replace_with_new_with_higher_new_mining_level-expected.json')
        result = mapped[0].to_dict()
        self.check_expected_results(result, expected_loc, regen=False)

        # Since we manually insert a Package without using `map_uri`, a
        # ScannableURI should not have been created. An update to a package
        # by `map_uri` should also not create a ScannableURI
        scannable = ScannableURI.objects.all()
        self.assertEqual(0, scannable.count())

    def test_merge_packages_no_replace(self):
        download_url = 'http://testdomap3.com'
        existing_package, _created = packagedb.models.Package.objects.get_or_create(
            type='generic',
            name='pack',
            version='0.1',
            description='',
            download_url=download_url,
            sha1='beef',
        )
        new_package_data = ScannedPackage(
            type='generic',
            name='pack',
            version='0.2',
            description='Description Updated',
            download_url=download_url
        ).to_dict()
        merge_packages(existing_package, new_package_data, replace=False)
        expected_loc = self.get_test_loc('run_map/test_merge_packages_no_replace-expected.json')
        result = existing_package.to_dict()
        self.check_expected_results(result, expected_loc, regen=False)

    def test_merge_packages_with_replace(self):
        download_url = 'http://testdomap3.com'
        existing_package, _created = packagedb.models.Package.objects.get_or_create(
            type='generic',
            name='pack',
            version='0.1',
            description='',
            download_url=download_url,
            sha1='beef',
        )
        new_package_data = ScannedPackage(
            type='generic',
            name='pack',
            version='0.2',
            description='Description Updated',
            download_url=download_url,
        ).to_dict()
        merge_packages(existing_package, new_package_data, replace=True)
        expected_loc = self.get_test_loc('run_map/test_merge_packages_with_replace-expected.json')
        result = existing_package.to_dict()
        self.check_expected_results(result, expected_loc, regen=False)

    def test_merge_packages_different_sha1(self):
        download_url = 'http://testdomap3.com'
        existing_package, _created = packagedb.models.Package.objects.get_or_create(
            type='generic',
            name='pack',
            version='0.1',
            description='',
            download_url=download_url,
            sha1='beef',
        )
        new_package_data = ScannedPackage(
            type='generic',
            name='pack',
            version='0.2',
            description='Description Updated',
            download_url=download_url,
            sha1='feed'
        ).to_dict()
        with self.assertRaises(Exception) as e:
            merge_packages(existing_package, new_package_data)
            self.assertTrue('Mismatched sha1' in e.exception)
