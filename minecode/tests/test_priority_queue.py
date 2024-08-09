#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from django.test import TestCase as DjangoTestCase
from minecode.utils_test import JsonBasedTesting
from minecode.models import PriorityResourceURI
from minecode.management.commands import priority_queue
from packagedb.models import Package


class PriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    def test_process_request(self):
        package_count = Package.objects.all().count()
        self.assertEqual(0, package_count)

        purl_str = 'pkg:maven/org.apache.twill/twill-core@0.12.0'
        download_url = 'https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0.jar'
        purl_sources_str = f'{purl_str}?classifier=sources'
        sources_download_url = 'https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0-sources.jar'

        p = PriorityResourceURI.objects.create(uri=purl_str)
        priority_queue.process_request(p)

        package_count = Package.objects.all().count()
        self.assertEqual(2, package_count)

        purls = [
            (package.purl, package.download_url)
            for package in Package.objects.all()
        ]
        self.assertIn(
            (purl_str, download_url), purls
        )
        self.assertIn(
            (purl_sources_str, sources_download_url), purls
        )
