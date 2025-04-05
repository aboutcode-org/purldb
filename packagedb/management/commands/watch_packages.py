#
# Copyright (c) nexB Inc. and others. All rights reserved.
# PurlDB is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.core.management.base import BaseCommand

from commoncode import cliutils
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS
from packageurl import PackageURL
from univers.version_range import RANGE_CLASS_BY_SCHEMES

from packagedb.models import Package
from packagedb.tasks import get_and_index_new_purls

VERSION_CLASS_BY_PACKAGE_TYPE = {
    pkg_type: range_class.version_class for pkg_type, range_class in RANGE_CLASS_BY_SCHEMES.items()
}

PRIORITY_QUEUE_SUPPORTED_ECOSYSTEMS = ["maven", "npm"]


class Command(BaseCommand):
    help = "Watch all packages for their latest versions and add them to the priority queue for scanning and indexing."

    def add_arguments(self, parser):
        parser.add_argument("--purl", type=str, help="Specify a PURL to watch single package.")

    def handle(self, *args, **options):
        purl_value = options.get("purl")

        packages_qs = (
            Package.objects.filter(type__in=PRIORITY_QUEUE_SUPPORTED_ECOSYSTEMS)
            .filter(type__in=SUPPORTED_ECOSYSTEMS)
            .distinct("type", "namespace", "name")
            .order_by("type", "namespace", "name")
        )

        if purl_value:
            purl = PackageURL.from_string(purl_value)
            packages_qs = packages_qs.filter(
                type=purl.type, namespace=purl.namespace, name=purl.name
            )

        with cliutils.progressmanager(
            packages_qs,
            show_eta=True,
            show_percent=True,
        ) as packages:
            for package in packages:
                error = get_and_index_new_purls(package.package_url)

                if error:
                    self.stdout.write(
                        error,
                        self.style.NOTICE,
                    )
