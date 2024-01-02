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
from minecode import priority_router
from minecode.models import PriorityResourceURI
from packagedb.models import Package
from packageurl import PackageURL
from univers.version_range import RANGE_CLASS_BY_SCHEMES

VERSION_CLASS_BY_PACKAGE_TYPE = {
    pkg_type: range_class.version_class
    for pkg_type, range_class in RANGE_CLASS_BY_SCHEMES.items()
}


class Command(BaseCommand):
    help = "Watch the packages for their latest versions and add them to the priority queue for scanning and indexing."

    def handle(self, *args, **options):
        verbosity = options["verbosity"]

        packages = Package.objects.distinct("type", "namespace", "name").order_by(
            "type", "namespace", "name"
        )

        for package in packages:
            if package.type not in SUPPORTED_ECOSYSTEMS:
                self.stdout.write(
                    f"NOTICE: {package.type} ecosystem is not supported.",
                    self.style.NOTICE,
                )
                continue

            version_class = VERSION_CLASS_BY_PACKAGE_TYPE.get(package.type)
            latest_local = package.get_latest_version()
            latest_local_version = version_class(latest_local.version)
            all_versions = versions(str(package))
            sorted_versions = sorted(
                [version_class(version.value) for version in all_versions]
            )

            try:
                index_of_local_version = sorted_versions.index(latest_local_version)
            except ValueError:
                self.stdout.write(
                    f"NOTICE: {latest_local} not found upstream.", self.style.NOTICE
                )
                continue

            for version in sorted_versions[index_of_local_version + 1 :]:
                purl = str(
                    PackageURL(
                        type=package.type,
                        namespace=package.namespace,
                        name=package.name,
                        version=str(version),
                    )
                )
                if not priority_router.is_routable(purl):
                    self.stdout.write(
                        f"NOTICE: {purl} is not routable.", self.style.NOTICE
                    )
                    continue

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
