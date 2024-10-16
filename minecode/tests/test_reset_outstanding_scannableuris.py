#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import datetime

from django.test import TestCase as DjangoTestCase
from django.utils import timezone

from minecode.management.commands import reset_outstanding_scannableuris
from minecode.models import ScannableURI
from minecode.utils_test import JsonBasedTesting
from packagedb.models import Package


class ResetScannableURITests(JsonBasedTesting, DjangoTestCase):
    def test_process_request(self):
        purl_str = "pkg:maven/org.apache.twill/twill-core@0.12.0"
        download_url = "https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0.jar"

        p1 = Package.objects.create(
            type="maven",
            namespace="org.apache.twill",
            name="twill-core",
            version="0.12.0",
            download_url=download_url
        )
        time = timezone.now()
        s1 = ScannableURI.objects.create(
            uri=download_url,
            package=p1,
            scan_status=ScannableURI.SCAN_IN_PROGRESS,
            wip_date=time,
            scan_date=time,
        )

        purl_str2 = "pkg:maven/org.apache.twill/twill-core@0.13.0"
        download_url2 = "https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.13.0/twill-core-0.13.0.jar"

        time_delta = datetime.datetime.now() - datetime.timedelta(days=1.2)
        p2 = Package.objects.create(
            type="maven",
            namespace="org.apache.twill",
            name="twill-core",
            version="0.13.0",
            download_url=download_url2
        )
        s2 = ScannableURI.objects.create(
            uri=download_url2,
            package=p2,
            scan_status=ScannableURI.SCAN_IN_PROGRESS,
            scan_date=time_delta,
            wip_date=time_delta
        )

        self.assertEqual(ScannableURI.SCAN_IN_PROGRESS, s1.scan_status)
        self.assertEqual(ScannableURI.SCAN_IN_PROGRESS, s2.scan_status)
        reset_outstanding_scannableuris.reset_outstanding_scannableuris()
        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertEqual(ScannableURI.SCAN_IN_PROGRESS, s1.scan_status)
        self.assertEqual(ScannableURI.SCAN_NEW, s2.scan_status)
