#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import hashlib
import os

from commoncode.testcase import check_against_expected_json_file
from commoncode.testcase import FileBasedTesting

from minecode_pipelines.pipes import maven


class MavenMiscTest(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def test_maven_collector_index_checksum(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        props = self.get_test_loc("maven/index/nexus-maven-repository-index.properties")
        collector = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )
        self.assertIsNotNone(collector.index_checksum)
        self.assertEqual(len(collector.index_checksum), 64)
        int(collector.index_checksum, 16)

        collector2 = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )
        self.assertEqual(collector.index_checksum, collector2.index_checksum)

    def test_maven_get_packages_resume(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        props = self.get_test_loc("maven/index/nexus-maven-repository-index.properties")
        collector = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )

        all_packages = list(collector.get_packages())

        if len(all_packages) < 2:
            return

        first_purl = str(all_packages[0][0])
        collector2 = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )
        resumed_packages = list(collector2.get_packages(last_processed_purl=first_purl))

        self.assertEqual(len(resumed_packages), len(all_packages) - 1)
        for resumed, original in zip(resumed_packages, all_packages[1:]):
            self.assertEqual(str(resumed[0]), str(original[0]))

    def test_maven_get_packages_resume_nonexistent_purl(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        props = self.get_test_loc("maven/index/nexus-maven-repository-index.properties")
        collector = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )

        all_packages = list(collector.get_packages())
        collector2 = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )
        resumed_packages = list(
            collector2.get_packages(last_processed_purl="pkg:maven/nonexistent/package@0.0.0")
        )

        self.assertEqual(len(resumed_packages), 0)

    def test_maven_collector_tracks_last_processed_purl(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        props = self.get_test_loc("maven/index/nexus-maven-repository-index.properties")
        collector = maven.MavenNexusCollector(
            index_location=index,
            index_properties_location=props,
        )
        self.assertIsNone(collector.last_processed_purl)

        packages = list(collector.get_packages())
        if packages:
            self.assertIsNotNone(collector.last_processed_purl)
            self.assertEqual(
                collector.last_processed_purl, str(packages[-1][0])
            )

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
        check_against_expected_json_file(result, expected_loc, regen=False)

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
        check_against_expected_json_file(result, expected_loc, regen=False)

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
        check_against_expected_json_file(result, expected_loc, regen=False)

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
        check_against_expected_json_file(result, expected_loc, regen=False)

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
        check_against_expected_json_file(result, expected_loc, regen=False)

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
        check_against_expected_json_file(result, expected_loc, regen=False)

    def test_get_artifacts_defaults(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")
        result = [a.to_dict() for a in maven.get_artifacts(index)]
        expected_loc = self.get_test_loc("maven/index/expected_artifacts-defaults.json")
        check_against_expected_json_file(result, expected_loc)

    def test_get_artifacts_no_worthyness(self):
        index = self.get_test_loc("maven/index/nexus-maven-repository-index.gz")

        def worth(a):
            return True

        result = [a.to_dict() for a in maven.get_artifacts(index, worthyness=worth)]
        expected_loc = self.get_test_loc("maven/index/expected_artifacts-all-worthy.json")
        check_against_expected_json_file(result, expected_loc)

    def test_get_artifacts_defaults_increment(self):
        index = self.get_test_loc("maven/index/increment/nexus-maven-repository-index.445.gz")
        result = [a.to_dict() for a in maven.get_artifacts(index)]
        expected_loc = self.get_test_loc("maven/index/increment/expected_artifacts-defaults.json")
        check_against_expected_json_file(result, expected_loc)

    def test_get_artifacts_defaults_buggy(self):
        index = self.get_test_loc("maven/index/buggy/nexus-maven-repository-index.gz")
        result = [a.to_dict() for a in maven.get_artifacts(index)]
        expected_loc = self.get_test_loc("maven/index/buggy/expected_artifacts-defaults.json")
        check_against_expected_json_file(result, expected_loc)

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
