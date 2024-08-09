#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os

from commoncode.testcase import FileBasedTesting

from minecode.visitors import repodata


class TestRepoData(FileBasedTesting):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def test_get_pkg_infos(self):
        filelists_xml = self.get_test_loc(
            'repodata_rpms/repodata/filelists.xml')
        primary_xml = self.get_test_loc('repodata_rpms/repodata/primary.xml')
        other_xml = self.get_test_loc('repodata_rpms/repodata/other.xml')
        expected = [
            {
                u'build_time': '1442515098',
                u'buildhost': 'c1bk.rdu2.centos.org',
                u'href': 'python-ceilometerclient-1.5.0-1.el7.src.rpm',
                u'pkgid': '36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5',
                u'group': 'Development/Languages',
                u'end_header_range': '4876',
                u'archive_size': '99648',
                u'package_size': '101516',
                'epoch': '0',
                u'changelogs': [
                    {
                        u'date': '1387195200',
                        u'changelog': '- Update to upstream 1.0.8\n- New dependency: python-six',
                        u'author': 'Jakub Ruzicka <jruzicka@redhat.com> 1.0.8-1'
                    }
                ],
                'rel': '1.el7',
                'type': 'rpm',
                u'files': [
                    {
                       u'name': 'python-ceilometerclient-1.5.0.tar.gz'
                    },
                    {
                        u'name': 'python-ceilometerclient.spec'
                    }
                ],
                u'description': None,
                u'installed_size': '99230',
                u'file_time': '1446590411',
                'arch': 'src',
                'name': 'python-ceilometerclient',
                u'license': 'ASL 2.0',
                u'url': 'https://github.com/openstack/python-ceilometerclient',
                u'checksum': '36547e200627ea25c4e3fb6f9735d58e682f8e35cd815dceed796c83628e60d5',
                u'directories': [],
                u'summary':'Python API and CLI for OpenStack Ceilometer',
                u'start_header_range':'880',
                u'required_rpms':[
                    {
                        u'name': 'python-d2to1'
                    },
                    {
                        u'ver': '2.5.0',
                        u'epoch': '0',
                        u'flags': 'GE',
                        u'name': 'python-oslo-sphinx'
                    },
                    {
                        u'name': 'python-pbr'
                    },
                    {
                        u'name': 'python-setuptools'
                    },
                    {
                        u'name': 'python-sphinx'
                    },
                    {
                        u'name': 'python2-devel'
                    }
                ],
                u'sourcerpm': None,
                'ver': '1.5.0'
            }
        ]
        result = repodata.get_pkg_infos(filelists_xml, primary_xml, other_xml)
        self.assertEqual(expected, result)

    def test_get_url_for_tag(self):
        expected = 'repodata/4c31e7e12c7aa42cf4d7d0b6ab7166fad76b5e40ea18f911e4a820cfa68d1541-filelists.xml.gz'
        repomdxml_file = self.get_test_loc('repodata_rpms/repodata/repomd.xml')
        output = repodata.get_url_for_tag(repomdxml_file, 'filelists')
        self.assertEqual(expected, output)
