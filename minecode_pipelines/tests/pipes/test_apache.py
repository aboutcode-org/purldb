#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from commoncode.testcase import FileBasedTesting

from minecode_pipelines.pipes import apache


class ApacheMiscTest(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def test_parse_apache_path_common(self):
        paths = [
            "abdera/1.0/apache-abdera-1.0-src.tar.gz",
            "accumulo/1.10.1/accumulo-1.10.1-src.tar.gz",
            "answer/1.3.0-incubating/apache-answer-1.3.0-incubating-bin-darwin-amd64.tar.gz",
            "karaf/cellar/4.0.5/apache-karaf-cellar-4.0.5-src.tar.gz",
            "cxf/3.1.9/apache-cxf-3.1.9-src.tar.gz",
            "ws/commons/axiom/1_2_2/axiom-1.2.2-bin.zip",
            "avalon/framework/jars/avalon-framework-excalibur-test-4.0b1.jar",
            "avalon/logkit/v1.2/LogKit-1.2-bin.tar.gz",
        ]
        expected = [
            {
                "namespace": "",
                "name": "abdera",
                "version": "1.0",
                "file_name": "apache-abdera-1.0-src.tar.gz",
            },
            {
                "namespace": "",
                "name": "accumulo",
                "version": "1.10.1",
                "file_name": "accumulo-1.10.1-src.tar.gz",
            },
            {
                "namespace": "",
                "name": "answer",
                "version": "1.3.0-incubating",
                "file_name": "apache-answer-1.3.0-incubating-bin-darwin-amd64.tar.gz",
            },
            {
                "namespace": "karaf",
                "name": "cellar",
                "version": "4.0.5",
                "file_name": "apache-karaf-cellar-4.0.5-src.tar.gz",
            },
            {
                "namespace": "",
                "name": "cxf",
                "version": "3.1.9",
                "file_name": "apache-cxf-3.1.9-src.tar.gz",
            },
            {
                "namespace": "ws/commons",
                "name": "axiom",
                "version": "1_2_2",
                "file_name": "axiom-1.2.2-bin.zip",
            },
            None,
            None,
        ]

        for i, p in enumerate(paths):
            self.assertEqual(apache.parse_apache_path_common(p), expected[i])

    def test_parse_complex_with_special_word_markers(self):
        """
        Test paths where parsing boundaries are triggered by keywords like
        'jars', 'binaries', or 'source'.
        """
        cases = [
            (
                "avalon/framework/jars/avalon-framework-excalibur-test-4.0b1.jar",
                {
                    "namespace": "avalon",
                    "name": "framework",
                    "version": "",
                    "file_name": "avalon-framework-excalibur-test-4.0b1.jar",
                },
            ),
            (
                "avalon/merlin/binaries/3.0/avalon-merlin-3.0-dist.zip",
                {
                    "namespace": "avalon",
                    "name": "merlin",
                    "version": "3.0",
                    "file_name": "avalon-merlin-3.0-dist.zip",
                },
            ),
            (
                "avalon/merlin/jars/merlin-plugin-1.0.jar",
                {
                    "namespace": "avalon",
                    "name": "merlin",
                    "version": "",
                    "file_name": "merlin-plugin-1.0.jar",
                },
            ),
            (
                "ant/antlibs/antunit/source/apache-ant-antunit-1.5.0-src.tar.bz2",
                {
                    "namespace": "ant/antlibs",
                    "name": "antunit",
                    "version": "",
                    "file_name": "apache-ant-antunit-1.5.0-src.tar.bz2",
                },
            ),
            (
                "ant/antlibs/compress/binaries/apache-ant-compress-1.5-bin.zip",
                {
                    "namespace": "ant/antlibs",
                    "name": "compress",
                    "version": "",
                    "file_name": "apache-ant-compress-1.5-bin.zip",
                },
            ),
        ]
        for path, expected in cases:
            self.assertEqual(apache.parse_apache_path_complex(path), expected)

    def test_parse_complex_with_version_markers(self):
        """
        Test paths where parsing boundaries are explicitly triggered by version strings.
        """
        cases = [
            (
                "avalon/logkit/v1.2/LogKit-1.2-bin.tar.gz",
                {
                    "namespace": "avalon",
                    "name": "logkit",
                    "version": "1.2",
                    "file_name": "LogKit-1.2-bin.tar.gz",
                },
            ),
            (
                "avro/avro-1.10.0/java/avro-grpc-1.10.0-sources.jar",
                {
                    "namespace": "",
                    "name": "avro",
                    "version": "1.10.0",
                    "file_name": "avro-grpc-1.10.0-sources.jar",
                },
            ),
            (
                "airflow/providers/2.11/apache_airflow_providers_fab-1.5.4-py3-none-any.whl",
                {
                    "namespace": "airflow",
                    "name": "providers",
                    "version": "2.11",
                    "file_name": "apache_airflow_providers_fab-1.5.4-py3-none-any.whl",
                },
            ),
            (
                "beam/vendor/beam-vendor-calcite-1_40_0/0.1/apache-beam-f6ec9cb0c167815f942cf70a674f92a04819c83b-source-release.zip",
                {
                    "namespace": "beam/vendor",
                    "name": "beam-vendor-calcite-1_40_0",
                    "version": "0.1",
                    "file_name": "apache-beam-f6ec9cb0c167815f942cf70a674f92a04819c83b-source-release.zip",
                },
            ),
            (
                "groovy/2.5.23/distribution/apache-groovy-binary-2.5.23.zip",
                {
                    "namespace": "",
                    "name": "groovy",
                    "version": "2.5.23",
                    "file_name": "apache-groovy-binary-2.5.23.zip",
                },
            ),
            (
                "beam/2.73.0/prism/windows/arm64/apache_beam-v2.73.0-prism-windows-arm64.zip",
                {
                    "namespace": "",
                    "name": "beam",
                    "version": "2.73.0",
                    "file_name": "apache_beam-v2.73.0-prism-windows-arm64.zip",
                },
            ),
            (
                "netbeans/netbeans-maven-archetypes/netbeans-platform-app-archetype/netbeans-platform-app-archetype-1.24/netbeans-platform-app-archetype-1.24-source-release.zip",
                {
                    "namespace": "netbeans/netbeans-maven-archetypes",
                    "name": "netbeans-platform-app-archetype",
                    "version": "1.24",
                    "file_name": "netbeans-platform-app-archetype-1.24-source-release.zip",
                },
            ),
        ]
        for path, expected in cases:
            self.assertEqual(apache.parse_apache_path_complex(path), expected)

    def test_parse_complex_fallback_logic(self):
        """
        Test no version in path
        Only treat the version found in the path as the package version.
        A version found in the filename represents the file's own version,
        not necessary the package version.
        There are cases where a package contains multiple files, each with
        its own version.
        For instance,
        "/namespace/package/1.0.0/john-1.2.3.zip"
        "/namespace/package/1.0.0/doo-2.3.zip"
        """
        cases = [
            (
                "httpd/libapreq/libapreq-1.1.tar.gz",
                {
                    "namespace": "httpd",
                    "name": "libapreq",
                    "version": "",
                    "file_name": "libapreq-1.1.tar.gz",
                },
            ),
            (
                "airflow/providers/apache_airflow_providers_cncf_kubernetes-10.18.0.tar.gz",
                {
                    "namespace": "airflow",
                    "name": "providers",
                    "version": "",
                    "file_name": "apache_airflow_providers_cncf_kubernetes-10.18.0.tar.gz",
                },
            ),
        ]
        for path, expected in cases:
            self.assertEqual(apache.parse_apache_path_complex(path), expected)

    def test_parse_complex_release_candidate_markers(self):
        """
        Test handling for release candidate patterns like 'rc1', 'rc2'.
        """
        path = "deltacloud/rc1/deltacloud-client-1.1.0.gem"
        expected = {
            "namespace": "",
            "name": "deltacloud",
            "version": "rc1",
            "file_name": "deltacloud-client-1.1.0.gem",
        }

        self.assertEqual(apache.parse_apache_path_complex(path), expected)
