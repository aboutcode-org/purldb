#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from packagedcode.rpm import EVR

from mock import Mock
from mock import patch

from minecode.utils_test import mocked_requests_get_for_uris
from minecode.utils_test import JsonBasedTesting

from minecode.visitors import URI
from minecode.visitors.repodata import combine_list_of_dicts
from minecode.visitors.repodata import combine_dicts_using_pkgid
from minecode.visitors.repomd_parser import generate_rpm_objects
from minecode.visitors.repomd_parser import collect_rpm_packages_from_repomd

# TODO: add redhat repo test!


class TestRepomdParser(JsonBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_combine_list_of_dicts(self):
        expected = {'a': '1', 'b': '2', 'c': '3'}
        output = combine_list_of_dicts([{'a': '1'}, {'b': '2'}, {'c': '3'}])
        self.assertEqual(expected, output)

    def test_generate_rpm_objects(self):
        packages = [{'name': 'python-ceilometerclient', 'arch': 'src', 'ver': '1.5.0', 'rel': '1.el7', 'href': '/python-ceilometerclient-1.5.0-1.el7.src.rpm'}]
        repomdxml_url = 'http://vault.centos.org/7.1.1503/cloud/Source/openstack-liberty'
        rpms = list(generate_rpm_objects(packages, repomdxml_url))
        self.assertEqual(1, len(rpms))
        rpm = rpms[0]
        self.assertEqual('python-ceilometerclient', rpm.name)
        self.assertEqual(EVR(version='1.5.0', release='1.el7').to_string(), rpm.version)

    def test_collect_rpm_packages_from_repomd_cloudera(self):
        uri2loc = {
            'http://archive.cloudera.com/cm5/redhat/6/x86_64/cm/5.3.2/repodata/repomd.xml':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera/repomd.xml'),
            'http://archive.cloudera.com/cm5/redhat/6/x86_64/cm/5.3.2/repodata/filelists.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera/filelists.xml.gz'),
            'http://archive.cloudera.com/cm5/redhat/6/x86_64/cm/5.3.2/repodata/other.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera/other.xml.gz'),
            'http://archive.cloudera.com/cm5/redhat/6/x86_64/cm/5.3.2/repodata/primary.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera/primary.xml.gz'),
        }

        uri = 'http://archive.cloudera.com/cm5/redhat/6/x86_64/cm/5.3.2/repodata/repomd.xml'
        with patch('requests.get') as mock_http_get:
            mock_http_get.side_effect = lambda * args, **kwargs: mocked_requests_get_for_uris(uri2loc, *args, **kwargs)
            _uris, packages, _error = collect_rpm_packages_from_repomd(uri)

        expected_loc = self.get_test_loc('repodata_rpms/repomd_parser/cloudera/expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_collect_rpm_packages_from_repomd_centos(self):
        uri2loc = {
            'http://vault.centos.org/3.8/updates/x86_64/repodata/repomd.xml':
                self.get_test_loc('repodata_rpms/repomd_parser/centos/repomd.xml'),
            'http://vault.centos.org/3.8/updates/x86_64/repodata/filelists.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/centos/filelists.xml.gz'),
            'http://vault.centos.org/3.8/updates/x86_64/repodata/other.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/centos/other.xml.gz'),
            'http://vault.centos.org/3.8/updates/x86_64/repodata/primary.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/centos/primary.xml.gz'),
        }

        uri = 'http://vault.centos.org/3.8/updates/x86_64/repodata/repomd.xml'
        with patch('requests.get') as mock_http_get:
            mock_http_get.side_effect = lambda * args, **kwargs: mocked_requests_get_for_uris(uri2loc, *args, **kwargs)
            uris, packages, _error = collect_rpm_packages_from_repomd(uri)

        expected_uris = [
            URI(uri='http://vault.centos.org/3.8/updates/x86_64/RPMS/wireshark-0.99.2-EL3.1.x86_64.rpm'),
            URI(uri='http://vault.centos.org/3.8/updates/x86_64/RPMS/wireshark-gnome-0.99.2-EL3.1.x86_64.rpm'),
            URI(uri='http://vault.centos.org/3.8/updates/x86_64/RPMS/XFree86-100dpi-fonts-4.3.0-111.EL.x86_64.rpm')
        ]
        self.assertEqual(expected_uris, uris)

        expected_loc = self.get_test_loc('repodata_rpms/repomd_parser/centos/expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_collect_rpm_packages_from_repomd_cloudera_2(self):
        uri2loc = {
            'http://archive.cloudera.com/cm5/redhat/5/x86_64/cm/5.2.0/repodata/repomd.xml':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera2/repomd.xml'),
            'http://archive.cloudera.com/cm5/redhat/5/x86_64/cm/5.2.0/repodata/filelists.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera2/filelists.xml.gz'),
            'http://archive.cloudera.com/cm5/redhat/5/x86_64/cm/5.2.0/repodata/primary.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera2/primary.xml.gz'),
            'http://archive.cloudera.com/cm5/redhat/5/x86_64/cm/5.2.0/repodata/other.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/cloudera2/other.xml.gz'),
        }

        uri = 'http://archive.cloudera.com/cm5/redhat/5/x86_64/cm/5.2.0/repodata/repomd.xml'
        with patch('requests.get') as mock_http_get:
            mock_http_get.side_effect = lambda * args, **kwargs: mocked_requests_get_for_uris(uri2loc, *args, **kwargs)
            _uris, packages, _error = collect_rpm_packages_from_repomd(uri)

        expected_loc = self.get_test_loc('repodata_rpms/repomd_parser/cloudera2/expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_collect_rpm_packages_from_repomd_postgresql(self):
        uri2loc = {
            'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/repodata/repomd.xml':
                self.get_test_loc('repodata_rpms/repomd_parser/postgresql/repomd.xml'),
            'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/repodata/d5b4a2d13632cceb2a13a42fdb2887a22c1e262e6eeeb7270a80beec453392cd-filelists.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/postgresql/d5b4a2d13632cceb2a13a42fdb2887a22c1e262e6eeeb7270a80beec453392cd-filelists.xml.gz'),
            'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/repodata/fc8c4fa6295d68abddcf5bba71435ecf585c439b86d7e75e0ba9bf3951f914b5-other.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/postgresql/fc8c4fa6295d68abddcf5bba71435ecf585c439b86d7e75e0ba9bf3951f914b5-other.xml.gz'),
            'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/repodata/d5cb2a54df0aa000ac2a007b1d9b0d1f2e6a924d2d97584acbe654e59aa993e8-primary.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/postgresql/d5cb2a54df0aa000ac2a007b1d9b0d1f2e6a924d2d97584acbe654e59aa993e8-primary.xml.gz'),
        }

        uri = 'http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/repodata/repomd.xml'
        with patch('requests.get') as mock_http_get:
            mock_http_get.side_effect = lambda * args, **kwargs: mocked_requests_get_for_uris(uri2loc, *args, **kwargs)
            uris, packages, error = collect_rpm_packages_from_repomd(uri)
        self.assertEqual(None, error)
        expected_uris = [
            URI(uri='http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/skytools-92-debuginfo-3.1.5-1.rhel6.x86_64.rpm'),
            URI(uri='http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/repmgr92-2.0.2-4.rhel6.x86_64.rpm'),
            URI(uri='http://yum.postgresql.org/9.2/redhat/rhel-6-x86_64/pgagent_92-3.2.1-1.rhel6.x86_64.rpm')
        ]

        self.assertEqual(expected_uris, uris)
        expected_loc = self.get_test_loc('repodata_rpms/repomd_parser/postgresql/expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_collect_rpm_packages_from_repomd_opensuse(self):
        uri2loc = {
            'http://download.opensuse.org/distribution/12.3/repo/oss/suse/repodata/repomd.xml':
                self.get_test_loc('repodata_rpms/repomd_parser/opensuse/repomd.xml'),
            'http://download.opensuse.org/distribution/12.3/repo/oss/suse/repodata/09ed18eaa761fe64c863137db5c51fdb4e60fbb29d6c9b0c424e3119ba4875cd-filelists.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/opensuse/09ed18eaa761fe64c863137db5c51fdb4e60fbb29d6c9b0c424e3119ba4875cd-filelists.xml.gz'),
            'http://download.opensuse.org/distribution/12.3/repo/oss/suse/repodata/9c100bbff252834349ca677813f333881ce9d2ca9db8091ce387156ba7a22859-other.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/opensuse/9c100bbff252834349ca677813f333881ce9d2ca9db8091ce387156ba7a22859-other.xml.gz'),
            'http://download.opensuse.org/distribution/12.3/repo/oss/suse/repodata/314da4321afcff987bd3e28672e60f1a2324f2698480b84812f7ec0a1aef4041-primary.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/opensuse/314da4321afcff987bd3e28672e60f1a2324f2698480b84812f7ec0a1aef4041-primary.xml.gz'),
        }

        uri = 'http://download.opensuse.org/distribution/12.3/repo/oss/suse/repodata/repomd.xml'
        with patch('requests.get') as mock_http_get:
            mock_http_get.side_effect = lambda * args, **kwargs: mocked_requests_get_for_uris(uri2loc, *args, **kwargs)
            _uris, packages, _error = collect_rpm_packages_from_repomd(uri)

        expected_loc = self.get_test_loc('repodata_rpms/repomd_parser/opensuse/expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_collect_rpm_packages_from_repomd_pgpool(self):
        uri2loc = {
            'http://pgpool.net/yum/rpms/3.4/redhat/rhel-6-x86_64/repodata/repomd.xml':
                self.get_test_loc('repodata_rpms/repomd_parser/pgpool/repomd.xml'),
            'http://pgpool.net/yum/rpms/3.4/redhat/rhel-6-x86_64/repodata/filelists.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/pgpool/filelists.xml.gz'),
            'http://pgpool.net/yum/rpms/3.4/redhat/rhel-6-x86_64/repodata/other.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/pgpool/other.xml.gz'),
            'http://pgpool.net/yum/rpms/3.4/redhat/rhel-6-x86_64/repodata/primary.xml.gz':
                self.get_test_loc('repodata_rpms/repomd_parser/pgpool/primary.xml.gz'),
        }

        uri = 'http://pgpool.net/yum/rpms/3.4/redhat/rhel-6-x86_64/repodata/repomd.xml'
        with patch('requests.get') as mock_http_get:
            mock_http_get.side_effect = lambda * args, **kwargs: mocked_requests_get_for_uris(uri2loc, *args, **kwargs)
            _uris, packages, _error = collect_rpm_packages_from_repomd(uri)

        expected_loc = self.get_test_loc('repodata_rpms/repomd_parser/pgpool/expected.json')
        self.check_expected_results(packages, expected_loc, regen=False)

    def test_combine_dicts_using_pkgid(self):
        all_dicts = [
            {'pkgid': '36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5', 'name': 'python-ceilometerclient'},
            {'pkgid': '36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5', 'ver': '1.5.0'},
            {'pkgid': '36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5', 'rel': '1.el7'}
        ]
        expected = [
            {'pkgid': '36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5',
             'name': 'python-ceilometerclient',
             'rel': '1.el7',
             'ver': '1.5.0'}
        ]
        output = combine_dicts_using_pkgid(all_dicts)
        self.assertEqual(expected, output)
