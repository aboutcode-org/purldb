#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import sys

from minecode.management.commands import VerboseCommand
from packagedb.models import Package, DependentPackage, Party

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(VerboseCommand):
    def handle(self, *args, **options):
        packages = Package.objects.using('minecode').all()
        package_count = packages.count()
        iterator = packages.iterator(chunk_size=2000)
        unsaved_packages = []
        unsaved_dependencies = []
        unsaved_parties = []

        i = 0
        for package in iterator:
            if Package.objects.filter(download_url=package.download_url).exists():
                continue
            if not (i % 100) and unsaved_packages:
                Package.objects.bulk_create(
                    unsaved_packages
                )
                DependentPackage.objects.bulk_create(
                    unsaved_dependencies
                )
                Party.objects.bulk_create(
                    unsaved_parties
                )
                unsaved_packages = []
                unsaved_dependencies = []
                unsaved_parties = []
                print(f"  {i:,} / {package_count:,} saved")
            else:
                unsaved_packages.append(package)
                dependencies = package.dependencies.all()
                unsaved_dependencies.extend(list(dependencies))
                parties = package.parties.all()
                unsaved_parties.extend(list(parties))
                i += 1

        if unsaved_packages:
            Package.objects.bulk_create(
                unsaved_packages
            )
            DependentPackage.objects.bulk_create(
                unsaved_dependencies
            )
            Party.objects.bulk_create(
                unsaved_parties
            )
            unsaved_packages = []
            unsaved_dependencies = []
            unsaved_parties = []
            print(f"  {i:,} / {package_count:,} saved")
