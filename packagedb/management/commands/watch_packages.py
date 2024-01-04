#
# Copyright (c) nexB Inc. and others. All rights reserved.
# PurlDB is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.core.management.base import BaseCommand
from fetchcode.package_versions import SUPPORTED_ECOSYSTEMS
from fetchcode.package_versions import versions
from minecode.models import PriorityResourceURI
from packagedb.models import Package
from packageurl import PackageURL
from univers.version_range import RANGE_CLASS_BY_SCHEMES

VERSION_CLASS_BY_PACKAGE_TYPE = {
    pkg_type: range_class.version_class
    for pkg_type, range_class in RANGE_CLASS_BY_SCHEMES.items()
}

PRIORITY_QUEUE_SUPPORTED_ECOSYSTEMS = ["maven", "npm"]


class Command(BaseCommand):
    help = "Watch the packages for their latest versions and add them to the priority queue for scanning and indexing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--purl", type=str, help="Specify a PURL to watch single package."
        )

    def handle(self, *args, **options):
        verbosity = options.get("verbosity")
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

        for package in packages_qs:
            version_class = VERSION_CLASS_BY_PACKAGE_TYPE.get(package.type)
            latest_local = package.get_latest_version()
            latest_local_version = version_class(latest_local.version)
            all_versions = versions(str(package))
            sorted_versions = sorted(
                [version_class(version.value) for version in all_versions]
            )

            if latest_local_version not in sorted_versions:
                self.stdout.write(
                    f"NOTICE: {latest_local} not found upstream.",
                    self.style.NOTICE,
                )

            new_versions = [v for v in sorted_versions if v > latest_local_version]
            for version in new_versions:
                purl = str(
                    PackageURL(
                        type=package.type,
                        namespace=package.namespace,
                        name=package.name,
                        version=str(version),
                    )
                )

                priority_resource_uri = PriorityResourceURI.objects.insert(purl)

                if verbosity > 1:
                    if priority_resource_uri:
                        self.stdout.write(
                            f"INFO: {purl} queued for indexing",
                            self.style.SUCCESS,
                        )
                    else:
                        self.stdout.write(
                            f"INFO: {purl} already in queue for indexing",
                            self.style.WARNING,
                        )
