#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from operator import itemgetter
import json
import os
import re

from mock import patch
from unittest import mock

from django.test import TestCase as DjangoTestCase

from minecode.collectors import maven as maven_collector
from minecode.management.commands.run_map import map_uri
from minecode.management.commands.run_visit import visit_uri
from minecode.mappers import maven as maven_mapper
from minecode.models import ResourceURI
from minecode.utils_test import mocked_requests_get
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import model_to_dict
from minecode.visitors import maven as maven_visitor
import packagedb

from packagedcode.maven import _parse
from packageurl import PackageURL

# TODO: add tests from /maven-indexer/indexer-core/src/test/java/org/acche/maven/index/artifact


def sort_deps(results):
    """
    FIXME: UGLY TEMP WORKAROUND: we sort the results because of a PyMaven bug
    See https://github.com/sassoftware/pymaven/issues/11
    """
    if 'dependencies' in results:
        results['dependencies'].sort()
    elif results and 'metadata' in results[0]:
        for result in results:
            result['metadata']['dependencies'].sort()


class MavenMiscTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_get_entries(self):
        index = self.get_test_loc('maven/index/nexus-maven-repository-index.gz')
        fields = list(maven_visitor.ENTRY_FIELDS.keys()) + list(maven_visitor.ENTRY_FIELDS_OTHER.keys()) + list(maven_visitor.ENTRY_FIELDS_IGNORED.keys())
        fields = set(fields)
        result = list(maven_visitor.get_entries(index, fields=fields))
        expected_loc = self.get_test_loc('maven/index/expected_entries.json')
        self.check_expected_results(result, expected_loc, regen=False)

    def test_get_entries_increment(self):
        index = self.get_test_loc('maven/index/increment/nexus-maven-repository-index.445.gz')
        fields = list(maven_visitor.ENTRY_FIELDS.keys()) + list(maven_visitor.ENTRY_FIELDS_OTHER.keys()) + list(maven_visitor.ENTRY_FIELDS_IGNORED.keys())
        fields = set(fields)
        result = list(maven_visitor.get_entries(index, fields=fields))
        expected_loc = self.get_test_loc('maven/index/increment/expected_entries.json')
        self.check_expected_results(result, expected_loc, regen=False)

    def test_get_entries_buggy(self):
        index = self.get_test_loc('maven/index/buggy/nexus-maven-repository-index.gz')
        fields = list(maven_visitor.ENTRY_FIELDS.keys()) + list(maven_visitor.ENTRY_FIELDS_OTHER.keys()) + list(maven_visitor.ENTRY_FIELDS_IGNORED.keys())
        fields = set(fields)
        result = list(maven_visitor.get_entries(index, fields=fields))
        expected_loc = self.get_test_loc('maven/index/buggy/expected_entries.json')
        self.check_expected_results(result, expected_loc, regen=False)

    def test_get_artifacts_full(self):
        index = self.get_test_loc('maven/index/nexus-maven-repository-index.gz')

        fields = (
            list(maven_visitor.ENTRY_FIELDS) +
            list(maven_visitor.ENTRY_FIELDS_OTHER) +
            list(maven_visitor.ENTRY_FIELDS_IGNORED)
        )
        fields = set(fields)

        result = [a.to_dict() for a in maven_visitor.get_artifacts(index, fields, include_all=True)]
        expected_loc = self.get_test_loc('maven/index/expected_artifacts.json')
        self.check_expected_results(result, expected_loc, regen=False)

    def test_get_artifacts_increment(self):
        index = self.get_test_loc('maven/index/increment/nexus-maven-repository-index.445.gz')
        fields = list(maven_visitor.ENTRY_FIELDS.keys()) + list(maven_visitor.ENTRY_FIELDS_OTHER.keys()) + list(maven_visitor.ENTRY_FIELDS_IGNORED.keys())
        fields = set(fields)
        result = [a.to_dict() for a in maven_visitor.get_artifacts(index, fields, include_all=True)]
        expected_loc = self.get_test_loc('maven/index/increment/expected_artifacts.json')
        self.check_expected_results(result, expected_loc, regen=False)

    def test_get_artifacts_buggy(self):
        index = self.get_test_loc('maven/index/buggy/nexus-maven-repository-index.gz')
        fields = list(maven_visitor.ENTRY_FIELDS.keys()) + list(maven_visitor.ENTRY_FIELDS_OTHER.keys()) + list(maven_visitor.ENTRY_FIELDS_IGNORED.keys())
        fields = set(fields)
        result = [a.to_dict() for a in maven_visitor.get_artifacts(index, fields, include_all=True)]
        expected_loc = self.get_test_loc('maven/index/buggy/expected_artifacts.json')
        self.check_expected_results(result, expected_loc, regen=False)

    def test_get_artifacts_defaults(self):
        index = self.get_test_loc('maven/index/nexus-maven-repository-index.gz')
        result = [a.to_dict() for a in maven_visitor.get_artifacts(index)]
        expected_loc = self.get_test_loc('maven/index/expected_artifacts-defaults.json')
        self.check_expected_results(result, expected_loc)

    def test_get_artifacts_no_worthyness(self):
        index = self.get_test_loc('maven/index/nexus-maven-repository-index.gz')

        def worth(a):
            return True

        result = [a.to_dict() for a in maven_visitor.get_artifacts(index, worthyness=worth)]
        expected_loc = self.get_test_loc('maven/index/expected_artifacts-all-worthy.json')
        self.check_expected_results(result, expected_loc)

    def test_get_artifacts_defaults_increment(self):
        index = self.get_test_loc('maven/index/increment/nexus-maven-repository-index.445.gz')
        result = [a.to_dict() for a in maven_visitor.get_artifacts(index)]
        expected_loc = self.get_test_loc('maven/index/increment/expected_artifacts-defaults.json')
        self.check_expected_results(result, expected_loc)

    def test_get_artifacts_defaults_buggy(self):
        index = self.get_test_loc('maven/index/buggy/nexus-maven-repository-index.gz')
        result = [a.to_dict() for a in maven_visitor.get_artifacts(index)]
        expected_loc = self.get_test_loc('maven/index/buggy/expected_artifacts-defaults.json')
        self.check_expected_results(result, expected_loc)

    def test_build_artifact(self):
        entry = {
            u'i': u'0-alpha-1-20050407.154541-1.pom|1131488721000|-1|2|2|0|pom',
            u'm': u'1318447185654',
            u'u': u'org.apache|maven|archetypes|1|0-alpha-1-20050407.154541-1.pom'}

        result = maven_visitor.build_artifact(entry, include_all=True)
        result = result.to_dict()
        expected = dict([
            (u'group_id', u'org.apache'),
            (u'artifact_id', u'maven'),
            (u'version', u'archetypes'),
            (u'packaging', u'0-alpha-1-20050407.154541-1.pom'),
            (u'classifier', u'1'),
            (u'extension', u'pom'),
            (u'last_modified', '2005-11-08T22:25:21+00:00'),
            (u'size', None),
            (u'sha1', None),
            (u'name', None),
            (u'description', None),
            (u'src_exist', False),
            (u'jdoc_exist', False),
            (u'sig_exist', False),
            (u'sha256', None),
            (u'osgi', dict()),
            (u'classes', [])
        ])

        self.assertEqual(expected.items(), result.items())

    def test_build_url_and_filename_1(self):
        test = {'group_id': 'de.alpharogroup', 'artifact_id': 'address-book-domain',
                'version': '3.12.0', 'classifier': None, 'extension': 'jar'}
        expected = 'https://repo1.maven.org/maven2/de/alpharogroup/address-book-domain/3.12.0/address-book-domain-3.12.0.jar', 'address-book-domain-3.12.0.jar'
        self.assertEqual(expected, maven_visitor.build_url_and_filename(**test))

    def test_build_url_and_filename_2(self):
        test = {'group_id': 'de.alpharogroup', 'artifact_id': 'address-book-data', 'version': '3.12.0', 'classifier': None, 'extension': 'pom'}
        expected = 'https://repo1.maven.org/maven2/de/alpharogroup/address-book-data/3.12.0/address-book-data-3.12.0.pom', 'address-book-data-3.12.0.pom'
        self.assertEqual(expected, maven_visitor.build_url_and_filename(**test))

    def test_build_url_and_filename_3(self):
        test = {'group_id': 'de.alpharogroup', 'artifact_id': 'address-book-rest-web', 'version': '3.12.0', 'classifier': None, 'extension': 'war'}
        expected = 'https://repo1.maven.org/maven2/de/alpharogroup/address-book-rest-web/3.12.0/address-book-rest-web-3.12.0.war', 'address-book-rest-web-3.12.0.war'
        self.assertEqual(expected, maven_visitor.build_url_and_filename(**test))

    def test_build_url_and_filename_4(self):
        test = {'group_id': 'uk.com.robust-it', 'artifact_id': 'cloning', 'version': '1.9.5', 'classifier': 'sources', 'extension': 'jar'}
        expected = 'https://repo1.maven.org/maven2/uk/com/robust-it/cloning/1.9.5/cloning-1.9.5-sources.jar', 'cloning-1.9.5-sources.jar'
        self.assertEqual(expected, maven_visitor.build_url_and_filename(**test))

    def test_build_url_and_filename_with_alternate_base(self):
        test = {
            'group_id': 'uk.com.robust-it', 'artifact_id': 'cloning',
            'version': '1.9.5', 'classifier': 'sources', 'extension': 'jar',
            'base_repo_url': 'maven-index://'}
        expected = 'maven-index:///uk/com/robust-it/cloning/1.9.5/cloning-1.9.5-sources.jar', 'cloning-1.9.5-sources.jar'
        self.assertEqual(expected, maven_visitor.build_url_and_filename(**test))

    def test_build_maven_xml_url(self):
        test = {'group_id': 'de.alpharogroup', 'artifact_id': 'address-book-domain'}
        expected = 'https://repo1.maven.org/maven2/de/alpharogroup/address-book-domain/maven-metadata.xml'
        self.assertEqual(expected, maven_visitor.build_maven_xml_url(**test))


class MavenVisitorTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_MavenNexusIndexVisitor_uris(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz'
        test_loc = self.get_test_loc('maven/index/nexus-maven-repository-index.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven_visitor.MavenNexusIndexVisitor(uri)
        expected_loc = self.get_test_loc('maven/index/expected_uris.json')
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=False)

    def test_MavenNexusIndexPropertiesVisitor(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.properties'
        test_loc = self.get_test_loc('maven/index/increment/nexus-maven-repository-index.properties')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven_visitor.MavenNexusPropertiesVisitor(uri)
        expected_loc = self.get_test_loc('maven/index/increment/expected_properties_uris.json')
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=False)

    def test_MavenNexusIndexVisitor_uris_increment(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.445.gz'
        test_loc = self.get_test_loc('maven/index/increment/nexus-maven-repository-index.445.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven_visitor.MavenNexusIndexVisitor(uri)
        expected_loc = self.get_test_loc('maven/index/increment/expected_uris.json')
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=False)

    def test_MavenNexusIndexVisitor_uris_buggy(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz'
        test_loc = self.get_test_loc('maven/index/buggy/nexus-maven-repository-index.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven_visitor.MavenNexusIndexVisitor(uri)
        expected_loc = self.get_test_loc('maven/index/buggy/expected_uris.json')
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=False)

    def test_visit_uri_does_not_fail_on_incorrect_sha1(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz'
        resource_uri = ResourceURI.objects.insert(uri=uri)

        before = [p.id for p in ResourceURI.objects.all()]
        test_loc = self.get_test_loc('maven/index/buggy/nexus-maven-repository-index.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            visit_uri(resource_uri)

        if before:
            visited = ResourceURI.objects.exclude(id__in=before)
        else:
            visited = ResourceURI.objects.all()

        results = [model_to_dict(rec, fields=['uri', 'sha1']) for rec in visited]
        results = sorted(results, key=itemgetter('uri'))
        expected_loc = self.get_test_loc('maven/index/buggy/expected_visited_uris.json')
        self.check_expected_results(results, expected_loc, regen=False)
        visited.delete()

    def test_MavenPOMVisitor_data(self):
        uri = 'https://repo1.maven.org/maven2/classworlds/classworlds/1.1-alpha-2/classworlds-1.1-alpha-2.pom'
        test_loc = self.get_test_loc('maven/pom/classworlds-1.1-alpha-2.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = maven_visitor.MavenPOMVisitor(uri)
        self.assertEqual(None, uris)
        expected = open(test_loc, 'rb').read()
        self.assertEqual(expected, data)


class MavenEnd2EndTest(JsonBasedTesting, DjangoTestCase):

    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_MavenNexusIndexVisitor_with_run_visit_then_map_end2end(self):
        # setup
        before = sorted(p.id for p in ResourceURI.objects.all())
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.445.gz'

        resource_uri = ResourceURI.objects.insert(uri=uri)
        test_index = self.get_test_loc('maven/index/nexus-maven-repository-index.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_index)
            visit_uri(resource_uri)

        if before:
            visited = ResourceURI.objects.exclude(id__in=before)
        else:
            visited = ResourceURI.objects.all()

        results = list(model_to_dict(rec, exclude=['id']) for rec in visited)
        results = sorted(results, key=itemgetter('uri'))
        expected_loc = self.get_test_loc('maven/end2end/expected_visited_uris.json')
        self.check_expected_results(results, expected_loc, regen=False)

        pre_visited_uris = ResourceURI.objects.filter(
            uri__contains='maven-index://').exclude(id__in=before)

        self.assertTrue(
            all(ru.last_visit_date and not ru.last_map_date
                for ru in pre_visited_uris))

        package_ids_before = sorted(p.id for p in packagedb.models.Package.objects.all())

        # now onto mapping the previsited URIs
        # setup
        # test proper
        for res_uri in pre_visited_uris:
            map_uri(res_uri)

        newly_mapped = packagedb.models.Package.objects.filter(
            download_url__startswith='https://repo1.maven.org/maven2').exclude(id__in=package_ids_before)
        # check that the saved packages are there as planned
        self.assertEqual(19, newly_mapped.count())

        package_results = list(pac.to_dict() for pac in newly_mapped)
        expected_loc = self.get_test_loc('maven/end2end/expected_mapped_packages.json')
        self.check_expected_results(package_results, expected_loc, fields_to_remove=['package_sets'], regen=False)

        # check that the map status has been updated correctly
        visited_then_mapped = ResourceURI.objects.filter(uri__contains='maven-index://')
        self.assertTrue(all(ru.last_map_date for ru in visited_then_mapped))

    def test_visit_and_map_using_pom_with_unicode(self):
        uri = 'https://repo1.maven.org/maven2/edu/psu/swe/commons/commons-jaxrs/1.22/commons-jaxrs-1.22.pom'
        test_loc = self.get_test_loc('maven/end2end_unicode/commons-jaxrs-1.22.pom')

        before_uri = [p.id for p in ResourceURI.objects.all()]
        before_pkg = [p.id for p in packagedb.models.Package.objects.all()]

        resource_uri = ResourceURI.objects.insert(uri=uri)

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)
            map_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri)
        else:
            visited = ResourceURI.objects.all()

        uri_results = sorted(model_to_dict(rec, exclude=['id']) for rec in visited)
        expected_loc = self.get_test_loc('maven/end2end_unicode/expected_visited_commons-jaxrs-1.22.json')
        self.check_expected_results(uri_results, expected_loc, regen=False)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = sorted(pac.to_dict() for pac in mapped)
        expected_loc = self.get_test_loc('maven/end2end_unicode/expected_mapped_commons-jaxrs-1.22.json')
        self.check_expected_results(package_results, expected_loc, regen=False)

    def test_visit_and_map_using_pom_with_unicode_multisteps(self):
        # this test deals with a single POM and the results from
        # the index and the pom visit yielding packages

        # Step 1: map some index data
        before_pkg = [p.id for p in packagedb.models.Package.objects.all()]

        # this is a pre-visited as from the Maven index URI
        index_uri_test_loc = self.get_test_loc('maven/end2end_multisteps/commons-jaxrs-1.21-index-data.json')
        index_uri = json.load(open(index_uri_test_loc, 'rb'))
        idx_resource_uri = ResourceURI.objects.insert(**index_uri)

        map_uri(idx_resource_uri)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = sorted((pac.to_dict() for pac in mapped), key=lambda d: list(d.keys()))
        expected_loc = self.get_test_loc('maven/end2end_multisteps/expected_mapped_commons-jaxrs-1.21-from-index.json')
        self.check_expected_results(package_results, expected_loc, fields_to_remove=['package_sets'], regen=False)

        # Step 2: map a POM

        # this is a pre-visited URI as from a POM
        pom_uri_test_loc = self.get_test_loc('maven/end2end_multisteps/commons-jaxrs-1.21-pom-data.json')
        pom_uri = json.load(open(pom_uri_test_loc, 'rb'))
        pom_resource_uri = ResourceURI.objects.insert(**pom_uri)
        map_uri(pom_resource_uri)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = sorted((pac.to_dict() for pac in mapped), key=lambda d: list(d.keys()))
        expected_loc = self.get_test_loc('maven/end2end_multisteps/expected_mapped_commons-jaxrs-1.21-from-pom.json')
        self.check_expected_results(package_results, expected_loc, fields_to_remove=['package_sets'], regen=False)

    def test_visit_and_map_with_index(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.properties'
        test_loc = self.get_test_loc('maven/end2end_index/nexus-maven-repository-index.properties')

        before_uri = [p.id for p in ResourceURI.objects.all()]
        before_pkg = [p.id for p in packagedb.models.Package.objects.all()]

        resource_uri = ResourceURI.objects.insert(uri=uri)

        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri).order_by('uri')
        else:
            visited = ResourceURI.objects.all().order_by('uri')

        uri_results = list(model_to_dict(rec, exclude=['id']) for rec in visited)
        expected_loc = self.get_test_loc('maven/end2end_index/expected_visited_index.json')
        self.check_expected_results(uri_results, expected_loc, regen=False)

        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.543.gz'
        # Use a small index file for test cases
        test_loc = self.get_test_loc('maven/end2end_index/nexus-maven-repository-index.163.gz')

        resource_uri = ResourceURI.objects.get(uri=uri)
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri).order_by('uri')
        else:
            visited = ResourceURI.objects.all().order_by('uri')

        uri_results = list(model_to_dict(rec, exclude=['id']) for rec in visited)
        expected_loc = self.get_test_loc('maven/end2end_index/expected_visited_increment_index.json')
        self.check_expected_results(uri_results, expected_loc, regen=False)


class MavenXmlMetadataVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_maven_medatata_xml_file(self):
        uri = 'https://repo1.maven.org/maven2/st/digitru/identity-core/maven-metadata.xml'
        test_loc = self.get_test_loc('maven/maven-metadata/maven-metadata.xml')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven_visitor.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc('maven/maven-metadata/expected_maven_xml.json')
        self.check_expected_uris(uris, expected_loc)


class MavenHtmlIndexVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_maven_medatata_html_index_jcenter_1(self):
        uri = 'http://jcenter.bintray.com/'
        test_loc = self.get_test_loc('maven/html/jcenter.bintray.com.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven_visitor.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc('maven/html/visitor_expected_jcenter.bintray.com2.html.json')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_maven_medatata_html_index_jcenter_2(self):
        uri = 'http://jcenter.bintray.com/Action/app/'
        test_loc = self.get_test_loc('maven/html/app.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven_visitor.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc('maven/html/visitor_expected_app.html.json')
        self.check_expected_uris(uris, expected_loc)

    def test_visit_maven_medatata_html_index_jcenter_3(self):
        uri = "http://jcenter.bintray.com/'com/virtualightning'/stateframework-compiler/"
        test_loc = self.get_test_loc('maven/html/stateframework-compiler.html')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven_visitor.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc('maven/html/visitor_expected_stateframework-compiler.html.json')
        self.check_expected_uris(uris, expected_loc)


# FIXME: we should not need to call a visitor for testing a mapper
class MavenMapperVisitAndMapTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_visit_and_build_package_from_pom_axis(self):
        uri = 'https://repo1.maven.org/maven2/axis/axis/1.4/axis-1.4.pom'
        test_loc = self.get_test_loc('maven/mapper/axis-1.4.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/axis-1.4.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_visit_and_build_package_from_pom_commons_pool(self):
        uri = 'https://repo1.maven.org/maven2/commons-pool/commons-pool/1.5.7/commons-pool-1.5.7.pom'
        test_loc = self.get_test_loc('maven/mapper/commons-pool-1.5.7.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/commons-pool-1.5.7.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_visit_and_build_package_from_pom_struts(self):
        uri = 'https://repo1.maven.org/maven2/struts-menu/struts-menu/2.4.2/struts-menu-2.4.2.pom'
        test_loc = self.get_test_loc('maven/mapper/struts-menu-2.4.2.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/struts-menu-2.4.2.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_visit_and_build_package_from_pom_mysql(self):
        uri = 'https://repo1.maven.org/maven2/mysql/mysql-connector-java/5.1.27/mysql-connector-java-5.1.27.pom'
        test_loc = self.get_test_loc('maven/mapper/mysql-connector-java-5.1.27.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/mysql-connector-java-5.1.27.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_visit_and_build_package_from_pom_xbean(self):
        uri = 'https://repo1.maven.org/maven2/xbean/xbean-jmx/2.0/xbean-jmx-2.0.pom'
        test_loc = self.get_test_loc('maven/mapper/xbean-jmx-2.0.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/xbean-jmx-2.0.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_visit_and_build_package_from_pom_maven_all(self):
        uri = 'https://repo1.maven.org/maven2/date/yetao/maven/maven-all/1.0-RELEASE/maven-all-1.0-RELEASE.pom'
        test_loc = self.get_test_loc('maven/mapper/maven-all-1.0-RELEASE.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/maven-all-1.0-RELEASE.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_visit_and_build_package_from_pom_with_unicode(self):
        uri = 'https://repo1.maven.org/maven2/edu/psu/swe/commons/commons-jaxrs/1.21/commons-jaxrs-1.21.pom'
        test_loc = self.get_test_loc('maven/mapper/commons-jaxrs-1.21.pom')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven_visitor.MavenPOMVisitor(uri)
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/mapper/commons-jaxrs-1.21.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)


class MavenMapperGetPackageTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_get_package_from_pom_1(self):
        test_loc = self.get_test_loc('maven/parsing/parse/jds-3.0.1.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/parse/jds-3.0.1.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_2(self):
        test_loc = self.get_test_loc('maven/parsing/parse/springmvc-rest-docs-maven-plugin-1.0-RC1.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/parse/springmvc-rest-docs-maven-plugin-1.0-RC1.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_3(self):
        test_loc = self.get_test_loc('maven/parsing/parse/jds-2.17.0718b.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/parse/jds-2.17.0718b.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_4(self):
        test_loc = self.get_test_loc('maven/parsing/parse/maven-javanet-plugin-1.7.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/parse/maven-javanet-plugin-1.7.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_5(self):
        test_loc = self.get_test_loc('maven/parsing/loop/coreplugin-1.0.0.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/coreplugin-1.0.0.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_6(self):
        test_loc = self.get_test_loc('maven/parsing/loop/argus-webservices-2.7.0.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/argus-webservices-2.7.0.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_7(self):
        test_loc = self.get_test_loc('maven/parsing/loop/pkg-2.0.13.1005.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/pkg-2.0.13.1005.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_8(self):
        test_loc = self.get_test_loc('maven/parsing/loop/ojcms-beans-0.1-beta.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/ojcms-beans-0.1-beta.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_9(self):
        test_loc = self.get_test_loc('maven/parsing/loop/jacuzzi-annotations-0.2.1.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/jacuzzi-annotations-0.2.1.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_10(self):
        test_loc = self.get_test_loc('maven/parsing/loop/argus-webservices-2.8.0.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/argus-webservices-2.8.0.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_11(self):
        test_loc = self.get_test_loc('maven/parsing/loop/jacuzzi-database-0.2.1.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/loop/jacuzzi-database-0.2.1.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_12(self):
        test_loc = self.get_test_loc('maven/parsing/empty/common-object-1.0.2.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/empty/common-object-1.0.2.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_get_package_from_pom_13(self):
        test_loc = self.get_test_loc('maven/parsing/empty/osgl-http-1.1.2.pom')
        data = open(test_loc).read()
        package = maven_mapper.get_package(data).to_dict()
        expected_loc = self.get_test_loc('maven/parsing/empty/osgl-http-1.1.2.pom.package.json')
        self.check_expected_results(package, expected_loc, regen=False)

    def test_regex_maven_pom_mapper_1(self):
        regex = re.compile(r'^https?://repo1.maven.org/maven2/.*\.pom$')
        result = re.match(regex, 'https://repo1.maven.org/maven2/com/google/appengine/appengine-api-1.0-sdk/1.2.0/appengine-api-1.0-sdk-1.2.0.pom')
        self.assertTrue(result)

    def test_MavenNexusIndexVisitor_uris_increment_contain_correct_purl(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.457.gz'
        test_loc = self.get_test_loc('maven/index/increment2/nexus-maven-repository-index.457.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven_visitor.MavenNexusIndexVisitor(uri)
        uris = [u for i, u in enumerate(uris) if i % 500 == 0]
        expected_loc = self.get_test_loc('maven/index/increment2/expected_uris.json')
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=False)

    def test_MavenNexusIndexVisitor_then_get_mini_package_from_index_data(self):
        uri = 'https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.457.gz'
        test_loc = self.get_test_loc('maven/index/increment2/nexus-maven-repository-index.457.gz')
        with patch('requests.get') as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven_visitor.MavenNexusIndexVisitor(uri)
        results = []
        for i, u in enumerate(uris):
            # only get a few records
            if i % 500 == 0:
                minip = maven_mapper.get_mini_package(u.data, u.uri, u.package_url)
                results.append(minip and minip.to_dict() or minip)
        expected_loc = self.get_test_loc('maven/index/increment2/expected_mini_package.json')
        self.check_expected_results(results, expected_loc, regen=False)

    def test_get_package_from_pom_does_create_a_correct_qualifier(self):
        'https://repo1.maven.org/maven2/org/hspconsortium/reference/hspc-reference-auth-server-webapp/1.9.1/hspc-reference-auth-server-webapp-1.9.1.pom'


class MavenPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):
        super(MavenPriorityQueueTests, self).setUp()

        expected_pom_loc = self.get_test_loc('maven/pom/classworlds-1.1.pom')
        with open(expected_pom_loc) as f:
            self.expected_pom_contents = f.read()

        self.scan_package = _parse(
            'maven_pom',
            'maven',
            'Java',
            text=self.expected_pom_contents,
        )

    def test_get_pom_text(self, regen=False):
        pom_contents = maven_collector.get_pom_text(
            namespace=self.scan_package.namespace,
            name=self.scan_package.name,
            version=self.scan_package.version
        )
        if regen:
            with open(self.expected_pom_loc, 'w') as f:
                f.write(pom_contents)
        self.assertEqual(self.expected_pom_contents, pom_contents)

    def test_get_package_sha1(self):
        sha1 = maven_collector.get_package_sha1(self.scan_package)
        expected_sha1 = '60c708f55deeb7c5dfce8a7886ef09cbc1388eca'
        self.assertEqual(expected_sha1, sha1)

    def test_map_maven_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string(self.scan_package.purl)
        maven_collector.map_maven_package(package_url, packagedb.models.PackageContentType.BINARY)
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = 'pkg:maven/classworlds/classworlds@1.1'
        self.assertEqual(expected_purl_str, package.purl)

    def test_map_maven_package_custom_repo_url(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        custom_repo_purl = "pkg:maven/org.eclipse.core/runtime@20070801?repository_url=https://packages.atlassian.com/mvn/maven-atlassian-external/"
        package_url = PackageURL.from_string(custom_repo_purl)
        maven_collector.map_maven_package(package_url, packagedb.models.PackageContentType.BINARY)
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_repo_url = 'https://packages.atlassian.com/mvn/maven-atlassian-external//org/eclipse/core/runtime/20070801/runtime-20070801.jar'
        self.assertEqual(expected_repo_url, package.download_url)


    def test_process_request(self):
        purl_str = 'pkg:maven/org.apache.twill/twill-core@0.12.0'
        download_url = 'https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0.jar'
        purl_sources_str = f'{purl_str}?classifier=sources'
        sources_download_url = 'https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0-sources.jar'
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        maven_collector.process_request(purl_str)
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(2, package_count)
        purls = [
            (package.purl, package.download_url)
            for package in packagedb.models.Package.objects.all()
        ]
        self.assertIn(
            (purl_str, download_url), purls
        )
        self.assertIn(
            (purl_sources_str, sources_download_url), purls
        )

    def test_fetch_parent(self, regen=False):
        pom_loc = self.get_test_loc('maven/pom/ant-antlr-1.10.1.pom')
        with open(pom_loc) as f:
            pom_text = f.read()
        parent_pom_text = maven_collector.fetch_parent(pom_text)
        expected_loc = self.get_test_loc('maven/pom/ant-parent-1.10.1.pom')

        if regen:
            with open(expected_loc, 'w') as f:
                f.write(parent_pom_text)

        with open(expected_loc) as f:
            expected_pom_text = f.read()
        self.assertEqual(expected_pom_text, parent_pom_text)

    def test_get_ancestry(self):
        pom_loc = self.get_test_loc('maven/pom/pulsar-client-1x-2.5.1.pom')
        with open(pom_loc) as f:
            pom_text = f.read()
        ancestor_pom_texts = list(maven_collector.get_ancestry(pom_text))
        expected_ancestor_pom_texts = []
        for expected_loc in [
            self.get_test_loc('maven/pom/apache-18.pom'),
            self.get_test_loc('maven/pom/pulsar-2.5.1.pom'),
            self.get_test_loc('maven/pom/pulsar-client-1x-base-2.5.1.pom')
        ]:
            with open(expected_loc) as f:
                expected_pom_text = f.read()
            expected_ancestor_pom_texts.append(expected_pom_text)
        self.assertEqual(expected_ancestor_pom_texts, ancestor_pom_texts)

    def test_merge_parent(self, regen=False):
        pom_loc = self.get_test_loc('maven/pom/ant-antlr-1.10.1.pom')
        with open(pom_loc) as f:
            pom_text = f.read()
        package = _parse(
            'maven_pom',
            'maven',
            'Java',
            text=pom_text
        )
        expected_before_loc = self.get_test_loc('maven/pom/ant-antlr-1.10.1-package_before.json')
        self.check_expected_results(package.to_dict(), expected_before_loc, regen=regen)

        parent_pom_loc = self.get_test_loc('maven/pom/ant-parent-1.10.1.pom')
        with open(parent_pom_loc) as f:
            parent_pom_text = f.read()
        parent_package = _parse(
            'maven_pom',
            'maven',
            'Java',
            text=parent_pom_text
        )
        package = maven_collector.merge_parent(package, parent_package)
        expected_after_loc = self.get_test_loc('maven/pom/ant-antlr-1.10.1-package_after.json')
        self.check_expected_results(package.to_dict(), expected_after_loc, regen=regen)

    def test_merge_ancestors(self, regen=False):
        pom_loc = self.get_test_loc('maven/pom/pulsar-client-1x-2.5.1.pom')
        with open(pom_loc) as f:
            pom_text = f.read()
        package = _parse(
            'maven_pom',
            'maven',
            'Java',
            text=pom_text
        )
        expected_before_loc = self.get_test_loc('maven/pom/pulsar-client-1x-2.5.1-package_before.json')
        self.check_expected_results(package.to_dict(), expected_before_loc, regen=regen)

        ancestor_pom_texts = []
        for loc in [
            self.get_test_loc('maven/pom/apache-18.pom'),
            self.get_test_loc('maven/pom/pulsar-2.5.1.pom'),
            self.get_test_loc('maven/pom/pulsar-client-1x-base-2.5.1.pom')
        ]:
            with open(loc) as f:
                pom_text = f.read()
            ancestor_pom_texts.append(pom_text)

        maven_collector.merge_ancestors(ancestor_pom_texts, package)
        expected_after_loc = self.get_test_loc('maven/pom/pulsar-client-1x-2.5.1-package_after.json')
        self.check_expected_results(package.to_dict(), expected_after_loc, regen=regen)

    @mock.patch("minecode.collectors.maven.get_pom_text")
    def test_get_merged_ancestor_package_from_maven_package(self, get_pom_text_mock, regen=False):
        get_pom_text_mock.return_value = ""
        ancestor_pom_texts = []
        with patch("minecode.collectors.maven.get_ancestry") as mock_get_ancestry:
            for loc in [
                self.get_test_loc('maven/pom/apache-18.pom'),
                self.get_test_loc('maven/pom/pulsar-2.5.1.pom'),
                self.get_test_loc('maven/pom/pulsar-client-1x-base-2.5.1.pom')
            ]:
                with open(loc) as f:
                    pom_text = f.read()
                ancestor_pom_texts.append(pom_text)
            mock_get_ancestry.return_value = ancestor_pom_texts
            db_package = packagedb.models.Package.objects.create(
                name="pulsar-client",
                namespace="org.apache.pulsar",
                version="2.5.1",
                type="maven",
                download_url="https://repo1.maven.org/maven2/org/apache/pulsar/pulsar-client/2.5.1/pulsar-client-2.5.1.jar",
            )
            merged_package = maven_collector.get_merged_ancestor_package_from_maven_package(package=db_package)
            expected_loc = self.get_test_loc('maven/pom/pulsar-client-merged-ancestor-package.json')
            self.check_expected_results(merged_package.to_dict(), expected_loc, regen=regen)


class MavenCrawlerFunctionsTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_check_if_file_name_is_linked_on_page(self):
        links = ['foo/', 'bar/', 'baz/']
        self.assertTrue(
            maven_collector.check_if_file_name_is_linked_on_page('foo/', links)
        )
        self.assertFalse(
            maven_collector.check_if_file_name_is_linked_on_page('qux/', links)
        )

    def test_check_if_page_has_pom_files(self):
        links1 = ['foo/', 'bar.jar', 'bar.pom']
        links2 = ['foo/', 'bar.jar']
        self.assertTrue(maven_collector.check_if_page_has_pom_files(links1))
        self.assertFalse(maven_collector.check_if_page_has_pom_files(links2))

    def test_check_if_page_has_directories(self):
        links1 = ['foo/', 'bar/', 'baz/']
        links2 = ['../', 'bar.pom', 'bar.jar']
        self.assertTrue(maven_collector.check_if_page_has_directories(links1))
        self.assertFalse(maven_collector.check_if_page_has_directories(links2))

    def test_check_if_package_version_page(self):
        links1 = ['../', 'bar.pom', 'bar.jar']
        links2 = ['../', 'foo/', 'bar/', 'baz/']
        self.assertTrue(maven_collector.check_if_package_version_page(links1))
        self.assertFalse(maven_collector.check_if_package_version_page(links2))

    def test_check_if_package_page(self):
        links1 = ['../', 'maven-metadata.xml']
        links2 = ['../', 'bar.pom', 'bar.jar']
        self.assertTrue(maven_collector.check_if_package_page(links1))
        self.assertFalse(maven_collector.check_if_package_page(links2))

    def test_check_if_maven_root(self):
        links1 = ['../', 'archetype-catalog.xml']
        links2 = ['../', 'bar.pom', 'bar.jar']
        self.assertTrue(maven_collector.check_if_maven_root(links1))
        self.assertFalse(maven_collector.check_if_maven_root(links2))

    @mock.patch('requests.get')
    def test_check_on_page(self, mock_request_get):
        checker = maven_collector.check_if_page_has_pom_files
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="parent-7.11.0.pom" title="parent-7.11.0.pom">parent-7.11.0.pom</a>'
        self.assertTrue(maven_collector.check_on_page('https://repo1.maven.org/maven2/net/shibboleth/parent/7.11.0/', checker))

    @mock.patch('requests.get')
    def test_is_maven_root(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="archetype-catalog.xml" title="archetype-catalog.xml">archetype-catalog.xml</a>'
        self.assertTrue(maven_collector.is_maven_root('https://repo1.maven.org/maven2/'))

    @mock.patch('requests.get')
    def test_is_package_page(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="maven-metadata.xml" title="maven-metadata.xml">maven-metadata.xml</a>'
        self.assertTrue(maven_collector.is_package_page('https://repo1.maven.org/maven2/xml-apis/xml-apis/'))

    @mock.patch('requests.get')
    def test_is_package_version_page(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '''
        <a href="../" title="../">../</a>
        <a href="parent-7.11.0.pom" title="parent-7.11.0.pom">parent-7.11.0.pom</a>
        '''
        self.assertTrue(maven_collector.is_package_version_page('https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/'))

    def test_url_parts(self):
        url = 'https://example.com/foo/bar/baz.jar'
        scheme, netloc, path_segments = maven_collector.url_parts(url)
        self.assertEqual('https', scheme)
        self.assertEqual('example.com', netloc)
        self.assertEquals(['foo', 'bar', 'baz.jar'], path_segments)

    def test_create_url(self):
        scheme = 'https'
        netloc = 'example.com'
        path_segments = ['foo', 'bar', 'baz.jar']
        url = 'https://example.com/foo/bar/baz.jar'
        self.assertEqual(
            url,
            maven_collector.create_url(scheme, netloc, path_segments)
        )

    @mock.patch('requests.get')
    def test_get_maven_root(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="archetype-catalog.xml" title="archetype-catalog.xml">archetype-catalog.xml</a>'
        self.assertEqual(
            'https://repo1.maven.org/maven2',
            maven_collector.get_maven_root('https://repo1.maven.org/maven2/net/shibboleth/parent/7.11.0/')
        )

    @mock.patch('requests.get')
    def test_determine_namespace_name_version_from_url(self, mock_request_get):
        url = 'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2'
        root_url = 'https://repo1.maven.org/maven2'

        package_page_text = '''
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                           2005-09-20 05:53         -
        <a href="maven-metadata.xml" title="maven-metadata.xml">maven-metadata.xml</a>
                                2012-06-26 17:01       567
        '''
        package_page = mock.Mock(ok=True, text=package_page_text)

        package_version_page_text = '''
        <a href="../">../</a> -
        <a href="xml-apis-1.0.b2.pom" title="xml-apis-1.0.b2.pom">xml-apis-1.0.b2.pom</a>
                               2005-09-20 05:53      2249
        '''
        package_version_page = mock.Mock(ok=True, text=package_version_page_text)
        mock_request_get.side_effect = [
            mock.Mock(ok=True, text=''),
            mock.Mock(ok=True, text=''),
            package_page,
            mock.Mock(ok=True, text=''),
            package_version_page
        ]

        namespace, package_name, package_version = maven_collector.determine_namespace_name_version_from_url(url, root_url)
        self.assertEqual('xml-apis', namespace)
        self.assertEqual('xml-apis', package_name)
        self.assertEqual('1.0.b2', package_version)

    @mock.patch('requests.get')
    def test_add_to_import_queue(self, mock_request_get):
        from minecode.models import ImportableURI

        url = 'https://repo1.maven.org/maven2/xml-apis/xml-apis/'
        root_url = 'https://repo1.maven.org/maven2'

        package_page_text = '''
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                           2005-09-20 05:53         -
        <a href="maven-metadata.xml" title="maven-metadata.xml">maven-metadata.xml</a>
                                2012-06-26 17:01       567
        '''
        package_page = mock.Mock(ok=True, text=package_page_text)

        package_version_page_text = '''
        <a href="../">../</a> -
        <a href="xml-apis-1.0.b2.pom" title="xml-apis-1.0.b2.pom">xml-apis-1.0.b2.pom</a>
                               2005-09-20 05:53      2249
        '''
        package_version_page = mock.Mock(ok=True, text=package_version_page_text)
        mock_request_get.side_effect = [
            package_page,
            mock.Mock(ok=True, text=''),
            mock.Mock(ok=True, text=''),
            package_page,
            mock.Mock(ok=True, text=''),
            package_version_page
        ]

        self.assertEqual(0, ImportableURI.objects.all().count())
        maven_collector.add_to_import_queue(url, root_url )
        self.assertEqual(1, ImportableURI.objects.all().count())
        importable_uri = ImportableURI.objects.get(uri=url)
        self.assertEqual('pkg:maven/xml-apis/xml-apis', importable_uri.package_url)

    def test_filter_only_directories(self):
        timestamps_by_links = {
            '../': '-',
            'foo/': '-',
            'foo.pom': '2023-09-28',
        }
        expected = {
            'foo/': '-',
        }
        self.assertEqual(
            expected,
            maven_collector.filter_only_directories(timestamps_by_links)
        )

    def test_filter_for_artifacts(self):
        timestamps_by_links = {
            '../': '2023-09-28',
            'foo.pom': '2023-09-28',
            'foo.ejb3': '2023-09-28',
            'foo.ear': '2023-09-28',
            'foo.aar': '2023-09-28',
            'foo.apk': '2023-09-28',
            'foo.gem': '2023-09-28',
            'foo.jar': '2023-09-28',
            'foo.nar': '2023-09-28',
            'foo.so': '2023-09-28',
            'foo.swc': '2023-09-28',
            'foo.tar': '2023-09-28',
            'foo.tar.gz': '2023-09-28',
            'foo.war': '2023-09-28',
            'foo.xar': '2023-09-28',
            'foo.zip': '2023-09-28',
        }
        expected = {
            'foo.ejb3': '2023-09-28',
            'foo.ear': '2023-09-28',
            'foo.aar': '2023-09-28',
            'foo.apk': '2023-09-28',
            'foo.gem': '2023-09-28',
            'foo.jar': '2023-09-28',
            'foo.nar': '2023-09-28',
            'foo.so': '2023-09-28',
            'foo.swc': '2023-09-28',
            'foo.tar': '2023-09-28',
            'foo.tar.gz': '2023-09-28',
            'foo.war': '2023-09-28',
            'foo.xar': '2023-09-28',
            'foo.zip': '2023-09-28',
        }
        self.assertEqual(expected, maven_collector.filter_for_artifacts(timestamps_by_links))

    def test_collect_links_from_text(self):
        filter = maven_collector.filter_only_directories
        text = '''
        <a href="../">../</a>
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                                   2005-09-20 05:53         -
        <a href="1.2.01/" title="1.2.01/">1.2.01/</a>
                                                   2010-02-03 21:05         -
        '''
        expected = {
            '1.0.b2/': '2005-09-20 05:53',
            '1.2.01/': '2010-02-03 21:05'
        }
        self.assertEqual(
            expected,
            maven_collector.collect_links_from_text(text, filter=filter)
        )

    def test_create_absolute_urls_for_links(self):
        filter = maven_collector.filter_only_directories
        text = '''
        <a href="../">../</a>
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                                   2005-09-20 05:53         -
        <a href="1.2.01/" title="1.2.01/">1.2.01/</a>
                                                   2010-02-03 21:05         -
        '''
        url = 'https://repo1.maven.org/maven2/xml-apis/xml-apis/'
        expected = {
            'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/': '2005-09-20 05:53',
            'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.2.01/': '2010-02-03 21:05'
        }
        self.assertEqual(
            expected,
            maven_collector.create_absolute_urls_for_links(text, url, filter=filter)
        )

    @mock.patch('requests.get')
    def test_get_directory_links(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '''
        <a href="../">../</a>
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                                   2005-09-20 05:53         -
        <a href="1.2.01/" title="1.2.01/">1.2.01/</a>
                                                   2010-02-03 21:05         -
        '''
        url = 'https://repo1.maven.org/maven2/xml-apis/xml-apis/'
        expected = {
            'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/': '2005-09-20 05:53',
            'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.2.01/': '2010-02-03 21:05'
        }
        self.assertEqual(expected, maven_collector.get_directory_links(url))

    @mock.patch('requests.get')
    def test_get_artifact_links(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '''
        <a href="../">../</a>
        <a href="xml-apis-1.0.b2.jar" title="xml-apis-1.0.b2.jar">xml-apis-1.0.b2.jar</a>
                               2005-09-20 05:53    109318
        <a href="xml-apis-1.0.b2.pom" title="xml-apis-1.0.b2.pom">xml-apis-1.0.b2.pom</a>
                               2005-09-20 05:53      2249
        '''
        url = 'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/'
        expected = {
            'https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/xml-apis-1.0.b2.jar': '2005-09-20 05:53',
        }
        self.assertEqual(expected, maven_collector.get_artifact_links(url))

    def test_crawl_to_package(self):
        pass

    def test_crawl_maven_repo_from_root(self):
        pass

    @mock.patch('requests.get')
    def test_get_artifact_sha1(self, mock_request_get):
        sha1 = '3136ca936f64c9d68529f048c2618bd356bf85c9'
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = sha1
        self.assertEqual(sha1, maven_collector.get_artifact_sha1('https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/xml-apis-1.0.b2.jar.sha1'))

    def test_get_classifier_from_artifact_url(self):
        artifact_url = 'https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/livereload-jvm-0.2.0-onejar.jar'
        package_version_page_url = 'https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/'
        package_name = 'livereload-jvm'
        package_version = '0.2.0'
        classifier = maven_collector.get_classifier_from_artifact_url(
            artifact_url,
            package_version_page_url,
            package_name,
            package_version
        )
        self.assertEqual('onejar', classifier)
