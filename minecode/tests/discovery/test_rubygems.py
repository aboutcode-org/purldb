# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#



import codecs
import json
import os

from mock import Mock
from mock import patch

from commoncode.fileutils import file_name
from django.test import TestCase as DjangoTestCase

from discovery.utils_test import mocked_requests_get
from discovery.utils_test import JsonBasedTesting
from discovery.utils_test import model_to_dict

from discovery import mappers
from discovery import route
from discovery.models import ResourceURI
from discovery import visit_router
from discovery.mappers.rubygems import build_rubygem_packages_from_api_data
from discovery.mappers.rubygems import build_rubygem_packages_from_metadata
from discovery.mappers.rubygems import RubyGemsApiVersionsJsonMapper
from discovery.mappers.rubygems import RubyGemsPackageArchiveMetadataMapper

from discovery.visitors.rubygems import get_gem_metadata
from discovery.visitors.rubygems import RubyGemsApiManyVersionsVisitor
from discovery.visitors.rubygems import RubyGemsIndexVisitor
from discovery.visitors.rubygems import RubyGemsPackageArchiveMetadataVisitor


#
# TODO: also parse Gemspec
# ('rubygems/address_standardization.gemspec', 'rubygems/address_standardization.gemspec.json'),
# ('rubygems/arel.gemspec', 'rubygems/arel.gemspec.json'),


class RubyGemsVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_check_gem_file_visitor_routes(self):
        routes = [
            'https://rubygems.org/downloads/m2r-2.1.0.gem',  # https
            'http://rubygems.org/downloads/m2r-2.1.0.gem',  # http
            'https://rubygems.org/downloads/O365RubyEasy-0.0.1.gem',  # upper
        ]

        for route in routes:
            self.assertTrue(visit_router.resolve(route))

    def test_RubyGemsIndexVisitor_latest(self):
        uri = 'http://rubygems.org/specs.4.8.gz'
        test_loc = self.get_test_loc('rubygems/index/latest_specs.4.8.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = RubyGemsIndexVisitor(uri)
        expected_loc = self.get_test_loc('rubygems/index/latest_specs.4.8.gz.expected.json')
        uris_list = list(uris)
        self.assertTrue(len(uris_list) > 1000)
        self.check_expected_uris(uris_list[0:1000], expected_loc, regen=False)

    def test_RubyGemsApiVersionVisitor(self):
        uri = 'https://rubygems.org/api/v1/versions/0xffffff.json'
        test_loc = self.get_test_loc('rubygems/apiv1/0xffffff.api.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = RubyGemsApiManyVersionsVisitor(uri)
        expected_loc = self.get_test_loc('rubygems/apiv1/expected_0xffffff.api.json')
        self.check_expected_results(data, expected_loc, regen=False)

    def test_RubyGemsApiVersionVisitor2(self):
        uri = 'https://rubygems.org/api/v1/versions/a1630ty_a1630ty.json'
        test_loc = self.get_test_loc('rubygems/apiv1/a1630ty_a1630ty.api.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = RubyGemsApiManyVersionsVisitor(uri)
        expected_loc = self.get_test_loc('rubygems/apiv1/expected_a1630ty_a1630ty.api.json')
        self.check_expected_results(data, expected_loc, regen=False)

    def test_RubyGemsApiVersionVisitor3(self):
        uri = 'https://rubygems.org/api/v1/versions/zuck.json'
        test_loc = self.get_test_loc('rubygems/apiv1/zuck.api.json')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = RubyGemsApiManyVersionsVisitor(uri)
        expected_loc = self.get_test_loc('rubygems/apiv1/expected_zuck.api.json')
        self.check_expected_results(data, expected_loc, regen=False)

    def test_RubyGemsPackageArchiveMetadataVisitor(self):
        uri = 'https://rubygems.org/downloads/a_okay-0.1.0.gem'
        test_loc = self.get_test_loc('rubygems/a_okay-0.1.0.gem', copy=True)
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = RubyGemsPackageArchiveMetadataVisitor(uri)
        expected_loc = self.get_test_loc('rubygems/a_okay-0.1.0.gem.metadata')
        with open(expected_loc) as expect_file:
            self.assertEquals(expect_file.read(), data)


class RubyGemsApiMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_build_rubygem_packages_from_api_data_1(self):
        with open(self.get_test_loc('rubygems/apiv1/0xffffff.api.json')) as api:
            apidata = json.load(api)
        packages = build_rubygem_packages_from_api_data(apidata, '0xffffff')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('rubygems/apiv1/0xffffff.api.package.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_rubygem_packages_from_api_data_2(self):
        with open(self.get_test_loc('rubygems/apiv1/zuck.api.json')) as api:
            apidata = json.load(api)
        packages = build_rubygem_packages_from_api_data(apidata, 'zuck')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('rubygems/apiv1/zuck.api.package.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_rubygem_packages_from_api_data_3(self):
        with open(self.get_test_loc('rubygems/apiv1/a1630ty_a1630ty.api.json')) as api:
            apidata = json.load(api)
        packages = mappers.rubygems.build_rubygem_packages_from_api_data(apidata, 'a1630ty_a1630ty')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('rubygems/apiv1/a1630ty_a1630ty.api.package.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_build_rubygem_packages_from_api_data_with_deps(self):
        with open(self.get_test_loc('rubygems/apiv1/action_tracker.api.json')) as api:
            apidata = json.load(api)
        packages = mappers.rubygems.build_rubygem_packages_from_api_data(apidata, 'action_tracker')
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('rubygems/apiv1/action_tracker.api.package.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_RubyGemsApiVersionsJsonMapper(self):
        test_uri = 'https://rubygems.org/api/v1/versions/a1630ty_a1630ty.json'
        router = route.Router()
        router.append(test_uri, RubyGemsApiVersionsJsonMapper)
        test_loc = self.get_test_loc('rubygems/apiv1/a1630ty_a1630ty.api.json')
        with codecs.open(test_loc, encoding='utf-8') as ltest_file:
            test_data = ltest_file.read()

        test_res_uri = ResourceURI(uri=test_uri, data=test_data)
        packages = RubyGemsApiVersionsJsonMapper(test_uri, test_res_uri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('rubygems/apiv1/a1630ty_a1630ty.api.mapped.json')
        self.check_expected_results(packages, expected_loc, regen=False)


class RubyGemsArchiveMapperTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_test_RubyGemsPackageArchiveMetadataMapper(self):
        test_uri = 'https://rubygems.org/downloads/mysmallidea-address_standardization-0.4.1.gem'
        router = route.Router()
        router.append(test_uri, RubyGemsPackageArchiveMetadataMapper)
        test_loc = self.get_test_loc('rubygems/mysmallidea-address_standardization-0.4.1.gem.metadata')
        with codecs.open(test_loc, encoding='utf-8') as test_file:
            test_data = test_file.read()

        test_res_uri = ResourceURI(uri=test_uri, data=test_data)
        packages = RubyGemsPackageArchiveMetadataMapper(test_uri, test_res_uri)
        packages = [p.to_dict() for p in packages]
        expected_loc = self.get_test_loc('rubygems/mysmallidea-address_standardization-0.4.1.gem.mapped.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def check_mapped_packages(self, test_loc, expected_loc, extract=True, regen=False):

        test_loc = self.get_test_loc(test_loc, copy=True)

        if extract:
            metadata = get_gem_metadata(test_loc)
        else:
            with open(test_loc) as tl:
                metadata = tl.read()

        download_url = 'https://rubygems.org/downloads/{}'.format(file_name(test_loc).replace('.metadata', ''))
        results = build_rubygem_packages_from_metadata(metadata, download_url)
        results = [p.to_dict() for p in results]

        expected_loc = self.get_test_loc(expected_loc)
        if regen:
            with codecs.open(expected_loc, 'wb', encoding='UTF-8') as ex:
                json.dump(results, ex, indent=2)

        with open(expected_loc) as ex:
            expected = json.load(ex)

        assert expected == results

    def test_build_rubygem_packages_from_metadata_plain(self):
        self.check_mapped_packages(
            'rubygems/0mq-0.4.1.gem.metadata',
            'rubygems/0mq-0.4.1.gem.package.json',
            extract=False)

    def test_build_rubygem_packages_from_metadata_0(self):
        self.check_mapped_packages(
            'rubygems/a_okay-0.1.0.gem',
            'rubygems/a_okay-0.1.0.gem.package.json')

    def test_build_rubygem_packages_from_metadata_1(self):
        self.check_mapped_packages(
            'rubygems/archive-tar-minitar-0.5.2.gem',
            'rubygems/archive-tar-minitar-0.5.2.gem.package.json')

    def test_build_rubygem_packages_from_metadata_2(self):
        self.check_mapped_packages(
            'rubygems/blankslate-3.1.3.gem',
            'rubygems/blankslate-3.1.3.gem.package.json')

    def test_build_rubygem_packages_from_metadata_3(self):
        self.check_mapped_packages(
            'rubygems/m2r-2.1.0.gem',
            'rubygems/m2r-2.1.0.gem.package.json')

    def test_build_rubygem_packages_from_metadata_4(self):
        self.check_mapped_packages(
            'rubygems/mysmallidea-address_standardization-0.4.1.gem',
            'rubygems/mysmallidea-address_standardization-0.4.1.gem.package.json')

    def test_build_rubygem_packages_from_metadata_5(self):
        self.check_mapped_packages(
            'rubygems/mysmallidea-mad_mimi_mailer-0.0.9.gem',
            'rubygems/mysmallidea-mad_mimi_mailer-0.0.9.gem.package.json')

    def test_build_rubygem_packages_from_metadata_6(self):
        self.check_mapped_packages(
            'rubygems/ng-rails-csrf-0.1.0.gem',
            'rubygems/ng-rails-csrf-0.1.0.gem.package.json')

    def test_build_rubygem_packages_from_metadata_7(self):
        self.check_mapped_packages(
            'rubygems/small_wonder-0.1.10.gem',
            'rubygems/small_wonder-0.1.10.gem.package.json')

    def test_build_rubygem_packages_from_metadata_8(self):
        self.check_mapped_packages(
            'rubygems/small-0.2.gem',
            'rubygems/small-0.2.gem.package.json')

    def test_build_rubygem_packages_from_metadata_9(self):
        self.check_mapped_packages(
            'rubygems/sprockets-vendor_gems-0.1.3.gem',
            'rubygems/sprockets-vendor_gems-0.1.3.gem.package.json')

    def test_build_rubygem_packages_from_metadata_with_deps(self):
        self.check_mapped_packages(
            'rubygems/action_tracker-1.0.2.gem',
            'rubygems/action_tracker-1.0.2.gem.package.json')


class RubyEnd2EndTest(JsonBasedTesting, DjangoTestCase):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_and_map_end2end(self):
        from discovery.management.commands.run_visit import visit_uri
        from discovery.management.commands.run_map import map_uri
        import packagedb

        uri = 'https://rubygems.org/downloads/sprockets-vendor_gems-0.1.3.gem'
        test_loc = self.get_test_loc('rubygems/sprockets-vendor_gems-0.1.3.gem', copy=True)

        before_uri = [p.id for p in ResourceURI.objects.all()]
        before_pkg = [p.id for p in packagedb.models.Package.objects.all()]

        resource_uri = ResourceURI.objects.insert(uri=uri)

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should process all the test uris
            visit_uri(resource_uri)
            map_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri)
        else:
            visited = ResourceURI.objects.all()

        uri_results = [model_to_dict(rec, exclude=['id']) for rec in visited]
        expected_loc = self.get_test_loc('rubygems/sprockets-vendor_gems-0.1.3.gem.visited.json')
        self.check_expected_results(uri_results, expected_loc, regen=False)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = [pac.to_dict() for pac in mapped]
        expected_loc = self.get_test_loc('rubygems/sprockets-vendor_gems-0.1.3.gem.mapped.json')
        self.check_expected_results(package_results, expected_loc, regen=False)
