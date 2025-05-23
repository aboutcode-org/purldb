#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os
import re
from operator import itemgetter
from unittest.mock import patch

from django.test import TestCase as DjangoTestCase

import packagedb
from minecode.management.commands.run_map import map_uri
from minecode.management.commands.run_visit import visit_uri
from minecode.miners import maven
from minecode.models import ResourceURI
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting
from minecode.utils_test import mocked_requests_get
from minecode.utils_test import model_to_dict

# TODO: add tests from /maven-indexer/indexer-core/src/test/java/org/acche/maven/index/artifact


def sort_deps(results):
    """
    FIXME: UGLY TEMP WORKAROUND: we sort the results because of a PyMaven bug
    See https://github.com/sassoftware/pymaven/issues/11
    """
    if "dependencies" in results:
        results["dependencies"].sort()
    elif results and "metadata" in results[0]:
        for result in results:
            result["metadata"]["dependencies"].sort()


class MavenMiscTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_get_entries(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        fields = (
            list(maven.ENTRY_FIELDS.keys())
            + list(maven.ENTRY_FIELDS_OTHER.keys())
            + list(maven.ENTRY_FIELDS_IGNORED.keys())
        )
        fields = set(fields)
        result = list(maven.get_entries(index, fields=fields))
        expected_loc = self.get_test_loc("maven/index/expected_entries.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_get_entries_increment(self):
        index = self.get_test_loc("maven/index/increment/nexus-maven-repository-index.445.gz")
        fields = (
            list(maven.ENTRY_FIELDS.keys())
            + list(maven.ENTRY_FIELDS_OTHER.keys())
            + list(maven.ENTRY_FIELDS_IGNORED.keys())
        )
        fields = set(fields)
        result = list(maven.get_entries(index, fields=fields))
        expected_loc = self.get_test_loc("maven/index/increment/expected_entries.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_get_entries_buggy(self):
        index = self.get_test_loc("maven/index/buggy/nexus-maven-repository-index.gz")
        fields = (
            list(maven.ENTRY_FIELDS.keys())
            + list(maven.ENTRY_FIELDS_OTHER.keys())
            + list(maven.ENTRY_FIELDS_IGNORED.keys())
        )
        fields = set(fields)
        result = list(maven.get_entries(index, fields=fields))
        expected_loc = self.get_test_loc("maven/index/buggy/expected_entries.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_get_artifacts_full(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")

        fields = (
            list(maven.ENTRY_FIELDS)
            + list(maven.ENTRY_FIELDS_OTHER)
            + list(maven.ENTRY_FIELDS_IGNORED)
        )
        fields = set(fields)

        result = [a.to_dict() for a in maven.get_artifacts(index, fields, include_all=True)]
        expected_loc = self.get_test_loc("maven/index/expected_artifacts.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_get_artifacts_increment(self):
        index = self.get_test_loc("maven/index/increment/nexus-maven-repository-index.445.gz")
        fields = (
            list(maven.ENTRY_FIELDS.keys())
            + list(maven.ENTRY_FIELDS_OTHER.keys())
            + list(maven.ENTRY_FIELDS_IGNORED.keys())
        )
        fields = set(fields)
        result = [a.to_dict() for a in maven.get_artifacts(index, fields, include_all=True)]
        expected_loc = self.get_test_loc("maven/index/increment/expected_artifacts.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_get_artifacts_buggy(self):
        index = self.get_test_loc("maven/index/buggy/nexus-maven-repository-index.gz")
        fields = (
            list(maven.ENTRY_FIELDS.keys())
            + list(maven.ENTRY_FIELDS_OTHER.keys())
            + list(maven.ENTRY_FIELDS_IGNORED.keys())
        )
        fields = set(fields)
        result = [a.to_dict() for a in maven.get_artifacts(index, fields, include_all=True)]
        expected_loc = self.get_test_loc("maven/index/buggy/expected_artifacts.json")
        self.check_expected_results(result, expected_loc, regen=FIXTURES_REGEN)

    def test_get_artifacts_defaults(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        result = [a.to_dict() for a in maven.get_artifacts(index)]
        expected_loc = self.get_test_loc("maven/index/expected_artifacts-defaults.json")
        self.check_expected_results(result, expected_loc)

    def test_get_artifacts_no_worthyness(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")

        def worth(a):
            return True

        result = [a.to_dict() for a in maven.get_artifacts(index, worthyness=worth)]
        expected_loc = self.get_test_loc("maven/index/expected_artifacts-all-worthy.json")
        self.check_expected_results(result, expected_loc)

    def test_get_artifacts_defaults_increment(self):
        index = self.get_test_loc("maven/index/increment/nexus-maven-repository-index.445.gz")
        result = [a.to_dict() for a in maven.get_artifacts(index)]
        expected_loc = self.get_test_loc("maven/index/increment/expected_artifacts-defaults.json")
        self.check_expected_results(result, expected_loc)

    def test_get_artifacts_defaults_buggy(self):
        index = self.get_test_loc("maven/index/buggy/nexus-maven-repository-index.gz")
        result = [a.to_dict() for a in maven.get_artifacts(index)]
        expected_loc = self.get_test_loc("maven/index/buggy/expected_artifacts-defaults.json")
        self.check_expected_results(result, expected_loc)

    def test_build_artifact(self):
        entry = {
            "i": "0-alpha-1-20050407.154541-1.pom|1131488721000|-1|2|2|0|pom",
            "m": "1318447185654",
            "u": "org.apache|maven|archetypes|1|0-alpha-1-20050407.154541-1.pom",
        }

        result = maven.build_artifact(entry, include_all=True)
        result = result.to_dict()
        expected = dict(
            [
                ("group_id", "org.apache"),
                ("artifact_id", "maven"),
                ("version", "archetypes"),
                ("packaging", "0-alpha-1-20050407.154541-1.pom"),
                ("classifier", "1"),
                ("extension", "pom"),
                ("last_modified", "2005-11-08T22:25:21+00:00"),
                ("size", None),
                ("sha1", None),
                ("name", None),
                ("description", None),
                ("src_exist", False),
                ("jdoc_exist", False),
                ("sig_exist", False),
                ("sha256", None),
                ("osgi", dict()),
                ("classes", []),
            ]
        )

        self.assertEqual(expected.items(), result.items())

    def test_build_url_and_filename_1(self):
        test = {
            "group_id": "de.alpharogroup",
            "artifact_id": "address-book-domain",
            "version": "3.12.0",
            "classifier": None,
            "extension": "jar",
        }
        expected = (
            "https://repo1.maven.org/maven2/de/alpharogroup/address-book-domain/3.12.0/address-book-domain-3.12.0.jar",
            "address-book-domain-3.12.0.jar",
        )
        self.assertEqual(expected, maven.build_url_and_filename(**test))

    def test_build_url_and_filename_2(self):
        test = {
            "group_id": "de.alpharogroup",
            "artifact_id": "address-book-data",
            "version": "3.12.0",
            "classifier": None,
            "extension": "pom",
        }
        expected = (
            "https://repo1.maven.org/maven2/de/alpharogroup/address-book-data/3.12.0/address-book-data-3.12.0.pom",
            "address-book-data-3.12.0.pom",
        )
        self.assertEqual(expected, maven.build_url_and_filename(**test))

    def test_build_url_and_filename_3(self):
        test = {
            "group_id": "de.alpharogroup",
            "artifact_id": "address-book-rest-web",
            "version": "3.12.0",
            "classifier": None,
            "extension": "war",
        }
        expected = (
            "https://repo1.maven.org/maven2/de/alpharogroup/address-book-rest-web/3.12.0/address-book-rest-web-3.12.0.war",
            "address-book-rest-web-3.12.0.war",
        )
        self.assertEqual(expected, maven.build_url_and_filename(**test))

    def test_build_url_and_filename_4(self):
        test = {
            "group_id": "uk.com.robust-it",
            "artifact_id": "cloning",
            "version": "1.9.5",
            "classifier": "sources",
            "extension": "jar",
        }
        expected = (
            "https://repo1.maven.org/maven2/uk/com/robust-it/cloning/1.9.5/cloning-1.9.5-sources.jar",
            "cloning-1.9.5-sources.jar",
        )
        self.assertEqual(expected, maven.build_url_and_filename(**test))

    def test_build_url_and_filename_with_alternate_base(self):
        test = {
            "group_id": "uk.com.robust-it",
            "artifact_id": "cloning",
            "version": "1.9.5",
            "classifier": "sources",
            "extension": "jar",
            "base_repo_url": "maven-index://",
        }
        expected = (
            "maven-index:///uk/com/robust-it/cloning/1.9.5/cloning-1.9.5-sources.jar",
            "cloning-1.9.5-sources.jar",
        )
        self.assertEqual(expected, maven.build_url_and_filename(**test))

    def test_build_maven_xml_url(self):
        test = {"group_id": "de.alpharogroup", "artifact_id": "address-book-domain"}
        expected = (
            "https://repo1.maven.org/maven2/de/alpharogroup/address-book-domain/maven-metadata.xml"
        )
        self.assertEqual(expected, maven.build_maven_xml_url(**test))


class MavenVisitorTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_MavenNexusIndexVisitor_uris(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz"
        test_loc = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven.MavenNexusIndexVisitor(uri)
        expected_loc = self.get_test_loc("maven/index/expected_uris.json")
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=FIXTURES_REGEN)

    def test_MavenNexusIndexPropertiesVisitor(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.properties"
        test_loc = self.get_test_loc(
            "maven/index/increment/nexus-maven-repository-index.properties"
        )
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven.MavenNexusPropertiesVisitor(uri)
        expected_loc = self.get_test_loc("maven/index/increment/expected_properties_uris.json")
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=FIXTURES_REGEN)

    def test_MavenNexusIndexVisitor_uris_increment(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.445.gz"
        test_loc = self.get_test_loc("maven/index/increment/nexus-maven-repository-index.445.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven.MavenNexusIndexVisitor(uri)
        expected_loc = self.get_test_loc("maven/index/increment/expected_uris.json")
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=FIXTURES_REGEN)

    def test_MavenNexusIndexVisitor_uris_buggy(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz"
        test_loc = self.get_test_loc("maven/index/buggy/nexus-maven-repository-index.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven.MavenNexusIndexVisitor(uri)
        expected_loc = self.get_test_loc("maven/index/buggy/expected_uris.json")
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=FIXTURES_REGEN)

    def test_visit_uri_does_not_fail_on_incorrect_sha1(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.gz"
        resource_uri = ResourceURI.objects.insert(uri=uri)

        before = [p.id for p in ResourceURI.objects.all()]
        test_loc = self.get_test_loc("maven/index/buggy/nexus-maven-repository-index.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            visit_uri(resource_uri)

        if before:
            visited = ResourceURI.objects.exclude(id__in=before)
        else:
            visited = ResourceURI.objects.all()

        results = [model_to_dict(rec, fields=["uri", "sha1"]) for rec in visited]
        results = sorted(results, key=itemgetter("uri"))
        expected_loc = self.get_test_loc("maven/index/buggy/expected_visited_uris.json")
        self.check_expected_results(results, expected_loc, regen=FIXTURES_REGEN)
        visited.delete()

    def test_MavenPOMVisitor_data(self):
        uri = "https://repo1.maven.org/maven2/classworlds/classworlds/1.1-alpha-2/classworlds-1.1-alpha-2.pom"
        test_loc = self.get_test_loc("maven/pom/classworlds-1.1-alpha-2.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, data, _ = maven.MavenPOMVisitor(uri)
        self.assertEqual(None, uris)
        expected = open(test_loc, "rb").read()
        self.assertEqual(expected, data)


class MavenEnd2EndTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_MavenNexusIndexVisitor_with_run_visit_then_map_end2end(self):
        # setup
        before = sorted(p.id for p in ResourceURI.objects.all())
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.445.gz"

        resource_uri = ResourceURI.objects.insert(uri=uri)
        test_index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_index)
            visit_uri(resource_uri)

        if before:
            visited = ResourceURI.objects.exclude(id__in=before)
        else:
            visited = ResourceURI.objects.all()

        results = list(model_to_dict(rec, exclude=["id"]) for rec in visited)
        results = sorted(results, key=itemgetter("uri"))
        expected_loc = self.get_test_loc("maven/end2end/expected_visited_uris.json")
        self.check_expected_results(results, expected_loc, regen=FIXTURES_REGEN)

        pre_visited_uris = ResourceURI.objects.filter(uri__contains="maven-index://").exclude(
            id__in=before
        )

        self.assertTrue(all(ru.last_visit_date and not ru.last_map_date for ru in pre_visited_uris))

        package_ids_before = sorted(p.id for p in packagedb.models.Package.objects.all())

        # now onto mapping the previsited URIs
        # setup
        # test proper
        for res_uri in pre_visited_uris:
            map_uri(res_uri)

        newly_mapped = packagedb.models.Package.objects.filter(
            download_url__startswith="https://repo1.maven.org/maven2"
        ).exclude(id__in=package_ids_before)
        # check that the saved packages are there as planned
        self.assertEqual(19, newly_mapped.count())

        package_results = list(pac.to_dict() for pac in newly_mapped)
        expected_loc = self.get_test_loc("maven/end2end/expected_mapped_packages.json")
        self.check_expected_results(
            package_results,
            expected_loc,
            fields_to_remove=["package_sets"],
            regen=FIXTURES_REGEN,
        )

        # check that the map status has been updated correctly
        visited_then_mapped = ResourceURI.objects.filter(uri__contains="maven-index://")
        self.assertTrue(all(ru.last_map_date for ru in visited_then_mapped))

    def test_visit_and_map_using_pom_with_unicode(self):
        uri = "https://repo1.maven.org/maven2/edu/psu/swe/commons/commons-jaxrs/1.22/commons-jaxrs-1.22.pom"
        test_loc = self.get_test_loc("maven/end2end_unicode/commons-jaxrs-1.22.pom")

        before_uri = [p.id for p in ResourceURI.objects.all()]
        before_pkg = [p.id for p in packagedb.models.Package.objects.all()]

        resource_uri = ResourceURI.objects.insert(uri=uri)

        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)
            map_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri)
        else:
            visited = ResourceURI.objects.all()

        uri_results = sorted(model_to_dict(rec, exclude=["id"]) for rec in visited)
        expected_loc = self.get_test_loc(
            "maven/end2end_unicode/expected_visited_commons-jaxrs-1.22.json"
        )
        self.check_expected_results(uri_results, expected_loc, regen=FIXTURES_REGEN)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = sorted(pac.to_dict() for pac in mapped)
        expected_loc = self.get_test_loc(
            "maven/end2end_unicode/expected_mapped_commons-jaxrs-1.22.json"
        )
        self.check_expected_results(package_results, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_map_using_pom_with_unicode_multisteps(self):
        # this test deals with a single POM and the results from
        # the index and the pom visit yielding packages

        # Step 1: map some index data
        before_pkg = [p.id for p in packagedb.models.Package.objects.all()]

        # this is a pre-visited as from the Maven index URI
        index_uri_test_loc = self.get_test_loc(
            "maven/end2end_multisteps/commons-jaxrs-1.21-index-data.json"
        )
        index_uri = json.load(open(index_uri_test_loc, "rb"))
        idx_resource_uri = ResourceURI.objects.insert(**index_uri)

        map_uri(idx_resource_uri)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = sorted((pac.to_dict() for pac in mapped), key=lambda d: list(d.keys()))
        expected_loc = self.get_test_loc(
            "maven/end2end_multisteps/expected_mapped_commons-jaxrs-1.21-from-index.json"
        )
        self.check_expected_results(
            package_results,
            expected_loc,
            fields_to_remove=["package_sets"],
            regen=FIXTURES_REGEN,
        )

        # Step 2: map a POM

        # this is a pre-visited URI as from a POM
        pom_uri_test_loc = self.get_test_loc(
            "maven/end2end_multisteps/commons-jaxrs-1.21-pom-data.json"
        )
        pom_uri = json.load(open(pom_uri_test_loc, "rb"))
        pom_resource_uri = ResourceURI.objects.insert(**pom_uri)
        map_uri(pom_resource_uri)

        if before_pkg:
            mapped = packagedb.models.Package.objects.exclude(id__in=before_pkg)
        else:
            mapped = packagedb.models.Package.objects.all()

        package_results = sorted((pac.to_dict() for pac in mapped), key=lambda d: list(d.keys()))
        expected_loc = self.get_test_loc(
            "maven/end2end_multisteps/expected_mapped_commons-jaxrs-1.21-from-pom.json"
        )
        self.check_expected_results(
            package_results,
            expected_loc,
            fields_to_remove=["package_sets"],
            regen=FIXTURES_REGEN,
        )

    def test_visit_and_map_with_index(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.properties"
        test_loc = self.get_test_loc("maven/end2end_index/nexus-maven-repository-index.properties")

        before_uri = [p.id for p in ResourceURI.objects.all()]

        resource_uri = ResourceURI.objects.insert(uri=uri)

        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri).order_by("uri")
        else:
            visited = ResourceURI.objects.all().order_by("uri")

        uri_results = list(model_to_dict(rec, exclude=["id"]) for rec in visited)
        expected_loc = self.get_test_loc("maven/end2end_index/expected_visited_index.json")
        self.check_expected_results(uri_results, expected_loc, regen=FIXTURES_REGEN)

        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.543.gz"
        # Use a small index file for test cases
        test_loc = self.get_test_loc("maven/end2end_index/nexus-maven-repository-index.163.gz")

        resource_uri = ResourceURI.objects.get(uri=uri)
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            # visit test proper: this should insert all the test_uris
            visit_uri(resource_uri)

        if before_uri:
            visited = ResourceURI.objects.exclude(id__in=before_uri).order_by("uri")
        else:
            visited = ResourceURI.objects.all().order_by("uri")

        # sort for stable order across OSes
        # https://github.com/aboutcode-org/purldb/issues/589
        uri_results = sorted(model_to_dict(rec, exclude=["id"]).items() for rec in visited)
        uri_results = [dict(i) for i in uri_results]

        expected_loc = self.get_test_loc(
            "maven/end2end_index/expected_visited_increment_index.json"
        )

        self.maxDiff = None
        self.check_expected_results(uri_results, expected_loc, regen=FIXTURES_REGEN)


class MavenXmlMetadataVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_visit_maven_medatata_xml_file(self):
        uri = "https://repo1.maven.org/maven2/st/digitru/identity-core/maven-metadata.xml"
        test_loc = self.get_test_loc("maven/maven-metadata/maven-metadata.xml")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc("maven/maven-metadata/expected_maven_xml.json")
        self.check_expected_uris(uris, expected_loc)


class MavenHtmlIndexVisitorTest(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_visit_maven_medatata_html_index_jcenter_1(self):
        uri = "http://jcenter.bintray.com/"
        test_loc = self.get_test_loc("maven/html/jcenter.bintray.com.html")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc(
            "maven/html/visitor_expected_jcenter.bintray.com2.html.json"
        )
        self.check_expected_uris(uris, expected_loc)

    def test_visit_maven_medatata_html_index_jcenter_2(self):
        uri = "http://jcenter.bintray.com/Action/app/"
        test_loc = self.get_test_loc("maven/html/app.html")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc("maven/html/visitor_expected_app.html.json")
        self.check_expected_uris(uris, expected_loc)

    def test_visit_maven_medatata_html_index_jcenter_3(self):
        uri = "http://jcenter.bintray.com/'com/virtualightning'/stateframework-compiler/"
        test_loc = self.get_test_loc("maven/html/stateframework-compiler.html")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _, _ = maven.MavenMetaDataVisitor(uri)
        expected_loc = self.get_test_loc(
            "maven/html/visitor_expected_stateframework-compiler.html.json"
        )
        self.check_expected_uris(uris, expected_loc)


# FIXME: we should not need to call a visitor for testing a mapper
class MavenMapperVisitAndMapTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_visit_and_build_package_from_pom_axis(self):
        uri = "https://repo1.maven.org/maven2/axis/axis/1.4/axis-1.4.pom"
        test_loc = self.get_test_loc("maven/mapper/axis-1.4.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/mapper/axis-1.4.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_build_package_from_pom_commons_pool(self):
        uri = (
            "https://repo1.maven.org/maven2/commons-pool/commons-pool/1.5.7/commons-pool-1.5.7.pom"
        )
        test_loc = self.get_test_loc("maven/mapper/commons-pool-1.5.7.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/mapper/commons-pool-1.5.7.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_build_package_from_pom_struts(self):
        uri = "https://repo1.maven.org/maven2/struts-menu/struts-menu/2.4.2/struts-menu-2.4.2.pom"
        test_loc = self.get_test_loc("maven/mapper/struts-menu-2.4.2.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/mapper/struts-menu-2.4.2.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_build_package_from_pom_mysql(self):
        uri = "https://repo1.maven.org/maven2/mysql/mysql-connector-java/5.1.27/mysql-connector-java-5.1.27.pom"
        test_loc = self.get_test_loc("maven/mapper/mysql-connector-java-5.1.27.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/mapper/mysql-connector-java-5.1.27.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_build_package_from_pom_xbean(self):
        uri = "https://repo1.maven.org/maven2/xbean/xbean-jmx/2.0/xbean-jmx-2.0.pom"
        test_loc = self.get_test_loc("maven/mapper/xbean-jmx-2.0.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/mapper/xbean-jmx-2.0.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_build_package_from_pom_maven_all(self):
        uri = "https://repo1.maven.org/maven2/date/yetao/maven/maven-all/1.0-RELEASE/maven-all-1.0-RELEASE.pom"
        test_loc = self.get_test_loc("maven/mapper/maven-all-1.0-RELEASE.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/mapper/maven-all-1.0-RELEASE.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_visit_and_build_package_from_pom_with_unicode(self):
        uri = "https://repo1.maven.org/maven2/edu/psu/swe/commons/commons-jaxrs/1.21/commons-jaxrs-1.21.pom"
        test_loc = self.get_test_loc("maven/mapper/commons-jaxrs-1.21.pom")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            _, data, _ = maven.MavenPOMVisitor(uri)
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/mapper/commons-jaxrs-1.21.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)


class MavenMapperGetPackageTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testfiles")

    def test_get_package_from_pom_1(self):
        test_loc = self.get_test_loc("maven/parsing/parse/jds-3.0.1.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/parse/jds-3.0.1.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_2(self):
        test_loc = self.get_test_loc(
            "maven/parsing/parse/springmvc-rest-docs-maven-plugin-1.0-RC1.pom"
        )
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/parsing/parse/springmvc-rest-docs-maven-plugin-1.0-RC1.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_3(self):
        test_loc = self.get_test_loc("maven/parsing/parse/jds-2.17.0718b.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/parse/jds-2.17.0718b.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_4(self):
        test_loc = self.get_test_loc("maven/parsing/parse/maven-javanet-plugin-1.7.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/parsing/parse/maven-javanet-plugin-1.7.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_5(self):
        test_loc = self.get_test_loc("maven/parsing/loop/coreplugin-1.0.0.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/loop/coreplugin-1.0.0.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_6(self):
        test_loc = self.get_test_loc("maven/parsing/loop/argus-webservices-2.7.0.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/parsing/loop/argus-webservices-2.7.0.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_7(self):
        test_loc = self.get_test_loc("maven/parsing/loop/pkg-2.0.13.1005.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/loop/pkg-2.0.13.1005.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_8(self):
        test_loc = self.get_test_loc("maven/parsing/loop/ojcms-beans-0.1-beta.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/loop/ojcms-beans-0.1-beta.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_9(self):
        test_loc = self.get_test_loc("maven/parsing/loop/jacuzzi-annotations-0.2.1.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/parsing/loop/jacuzzi-annotations-0.2.1.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_10(self):
        test_loc = self.get_test_loc("maven/parsing/loop/argus-webservices-2.8.0.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/parsing/loop/argus-webservices-2.8.0.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_11(self):
        test_loc = self.get_test_loc("maven/parsing/loop/jacuzzi-database-0.2.1.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc(
            "maven/parsing/loop/jacuzzi-database-0.2.1.pom.package.json"
        )
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_12(self):
        test_loc = self.get_test_loc("maven/parsing/empty/common-object-1.0.2.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/empty/common-object-1.0.2.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_get_package_from_pom_13(self):
        test_loc = self.get_test_loc("maven/parsing/empty/osgl-http-1.1.2.pom")
        data = open(test_loc).read()
        package = maven.get_package(data).to_dict()
        expected_loc = self.get_test_loc("maven/parsing/empty/osgl-http-1.1.2.pom.package.json")
        self.check_expected_results(package, expected_loc, regen=FIXTURES_REGEN)

    def test_regex_maven_pom_mapper_1(self):
        regex = re.compile(r"^https?://repo1.maven.org/maven2/.*\.pom$")
        result = re.match(
            regex,
            "https://repo1.maven.org/maven2/com/google/appengine/appengine-api-1.0-sdk/1.2.0/appengine-api-1.0-sdk-1.2.0.pom",
        )
        self.assertTrue(result)

    def test_MavenNexusIndexVisitor_uris_increment_contain_correct_purl(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.457.gz"
        test_loc = self.get_test_loc("maven/index/increment2/nexus-maven-repository-index.457.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven.MavenNexusIndexVisitor(uri)
        uris = [u for i, u in enumerate(uris) if i % 500 == 0]
        expected_loc = self.get_test_loc("maven/index/increment2/expected_uris.json")
        self.check_expected_uris(uris, expected_loc, data_is_json=True, regen=FIXTURES_REGEN)

    def test_MavenNexusIndexVisitor_then_get_mini_package_from_index_data(self):
        uri = "https://repo1.maven.org/maven2/.index/nexus-maven-repository-index.457.gz"
        test_loc = self.get_test_loc("maven/index/increment2/nexus-maven-repository-index.457.gz")
        with patch("requests.get") as mock_http_get:
            mock_http_get.return_value = mocked_requests_get(uri, test_loc)
            uris, _data, _errors = maven.MavenNexusIndexVisitor(uri)
        results = []
        for i, u in enumerate(uris):
            # only get a few records
            if i % 500 == 0:
                minip = maven.get_mini_package(u.data, u.uri, u.package_url)
                results.append(minip and minip.to_dict() or minip)
        expected_loc = self.get_test_loc("maven/index/increment2/expected_mini_package.json")
        self.check_expected_results(results, expected_loc, regen=FIXTURES_REGEN)
