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

    def test_parse_apache_path_complex(self):
        paths = [
            "avalon/framework/jars/avalon-framework-excalibur-test-4.0b1.jar",
            "avalon/logkit/v1.2/LogKit-1.2-bin.tar.gz",
            "avalon/merlin/binaries/3.0/avalon-merlin-3.0-dist.zip",
            "avalon/merlin/jars/merlin-plugin-1.0.jar",
            "avro/avro-1.10.0/java/avro-grpc-1.10.0-sources.jar",
            "httpd/libapreq/libapreq-1.1.tar.gz",
            "airflow/providers/apache_airflow_providers_cncf_kubernetes-10.18.0.tar.gz",
            "ace/apache-ace-2.1.0/apache-ace-2.1.0-src.zip",
            "avalon/excalibur/v4.0/Excalibur-4.0-bin.tar.gz",
            "airflow/providers/2.11/apache_airflow_providers_fab-1.5.4-py3-none-any.whl",
            "beam/vendor/beam-vendor-calcite-1_40_0/0.1/apache-beam-f6ec9cb0c167815f942cf70a674f92a04819c83b-source-release.zip",
            "groovy/2.5.23/distribution/apache-groovy-binary-2.5.23.zip",
            "groovy/2.5.23/sources/apache-groovy-src-2.5.23.zip",
            "geronimo/safeguard/safeguard-parent-1.2.1-source-release.zip",
            "beam/2.73.0/prism/windows/arm64/apache_beam-v2.73.0-prism-windows-arm64.zip",
            "ranger/2.7.0/plugins/hdfs/ranger-2.7.0-hdfs-plugin.tar.gz",
            "netbeans/netbeans-maven-archetypes/netbeans-platform-app-archetype/netbeans-platform-app-archetype-1.24/netbeans-platform-app-archetype-1.24-source-release.zip",
            "ant/antlibs/antunit/source/apache-ant-antunit-1.5.0-src.tar.bz2",
            "ant/antlibs/compress/binaries/apache-ant-compress-1.5-bin.zip",
            "asterixdb/asterixdb-0.9.8.1/apache-asterixdb-0.9.8.1-source-release.zip",
            "deltacloud/rc1/deltacloud-client-1.1.0.gem",
        ]
        expected = [
            {
                "namespace": "avalon",
                "name": "framework",
                "version": "",
                "file_name": "avalon-framework-excalibur-test-4.0b1.jar",
            },
            {
                "namespace": "avalon",
                "name": "logkit",
                "version": "1.2",
                "file_name": "LogKit-1.2-bin.tar.gz",
            },
            {
                "namespace": "avalon",
                "name": "merlin",
                "version": "3.0",
                "file_name": "avalon-merlin-3.0-dist.zip",
            },
            {
                "namespace": "avalon",
                "name": "merlin",
                "version": "",
                "file_name": "merlin-plugin-1.0.jar",
            },
            {
                "namespace": "",
                "name": "avro",
                "version": "1.10.0",
                "file_name": "avro-grpc-1.10.0-sources.jar",
            },
            {
                "namespace": "httpd",
                "name": "libapreq",
                "version": "",
                "file_name": "libapreq-1.1.tar.gz",
            },
            {
                "namespace": "airflow",
                "name": "providers",
                "version": "",
                "file_name": "apache_airflow_providers_cncf_kubernetes-10.18.0.tar.gz",
            },
            {
                "namespace": "",
                "name": "ace",
                "version": "2.1.0",
                "file_name": "apache-ace-2.1.0-src.zip",
            },
            {
                "namespace": "avalon",
                "name": "excalibur",
                "version": "4.0",
                "file_name": "Excalibur-4.0-bin.tar.gz",
            },
            {
                "namespace": "airflow",
                "name": "providers",
                "version": "2.11",
                "file_name": "apache_airflow_providers_fab-1.5.4-py3-none-any.whl",
            },
            {
                "namespace": "beam/vendor",
                "name": "beam-vendor-calcite-1_40_0",
                "version": "0.1",
                "file_name": "apache-beam-f6ec9cb0c167815f942cf70a674f92a04819c83b-source-release.zip",
            },
            {
                "namespace": "",
                "name": "groovy",
                "version": "2.5.23",
                "file_name": "apache-groovy-binary-2.5.23.zip",
            },
            {
                "namespace": "",
                "name": "groovy",
                "version": "2.5.23",
                "file_name": "apache-groovy-src-2.5.23.zip",
            },
            {
                "namespace": "geronimo",
                "name": "safeguard",
                "version": "",
                "file_name": "safeguard-parent-1.2.1-source-release.zip",
            },
            {
                "namespace": "",
                "name": "beam",
                "version": "2.73.0",
                "file_name": "apache_beam-v2.73.0-prism-windows-arm64.zip",
            },
            {
                "namespace": "",
                "name": "ranger",
                "version": "2.7.0",
                "file_name": "ranger-2.7.0-hdfs-plugin.tar.gz",
            },
            {
                "namespace": "netbeans/netbeans-maven-archetypes",
                "name": "netbeans-platform-app-archetype",
                "version": "1.24",
                "file_name": "netbeans-platform-app-archetype-1.24-source-release.zip",
            },
            {
                "namespace": "ant/antlibs",
                "name": "antunit",
                "version": "",
                "file_name": "apache-ant-antunit-1.5.0-src.tar.bz2",
            },
            {
                "namespace": "ant/antlibs",
                "name": "compress",
                "version": "",
                "file_name": "apache-ant-compress-1.5-bin.zip",
            },
            {
                "namespace": "",
                "name": "asterixdb",
                "version": "0.9.8.1",
                "file_name": "apache-asterixdb-0.9.8.1-source-release.zip",
            },
            {
                "namespace": "",
                "name": "deltacloud",
                "version": "",
                "file_name": "deltacloud-client-1.1.0.gem",
            },
        ]

        for i, p in enumerate(paths):
            self.assertEqual(apache.parse_apache_path_complex(p), expected[i])
