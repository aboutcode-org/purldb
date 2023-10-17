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

        print(f"Copying {package_count:,} Packages from the 'minecode' database to the 'default' database")
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
                new_package = Package(
                    filename=package.filename,
                    package_content=package.package_content,
                    type=package.type,
                    namespace=package.namespace,
                    name=package.name,
                    version=package.version,
                    qualifiers=package.qualifiers,
                    subpath=package.subpath,
                    primary_language=package.primary_language,
                    description=package.description,
                    release_date=package.release_date,
                    keywords=package.keywords,
                    homepage_url=package.homepage_url,
                    download_url=package.download_url,
                    bug_tracking_url=package.bug_tracking_url,
                    code_view_url=package.code_view_url,
                    vcs_url=package.vcs_url,
                    repository_homepage_url=package.repository_homepage_url,
                    repository_download_url=package.repository_download_url,
                    api_data_url=package.api_data_url,
                    size=package.size,
                    md5=package.md5,
                    sha1=package.sha1,
                    sha256=package.sha256,
                    sha512=package.sha512,
                    copyright=package.copyright,
                    holder=package.holder,
                    declared_license_expression=package.declared_license_expression,
                    license_detections=package.license_detections,
                    other_license_expression=package.other_license_expression,
                    other_license_detections=package.other_license_detections,
                    extracted_license_statement=package.extracted_license_statement,
                    source_packages=package.source_packages,
                    extra_data=package.extra_data,
                    datasource_id=package.datasource_id,
                    file_references=package.file_references,
                )
                unsaved_packages.append(new_package)

                for dependency in package.dependencies.all():
                    new_dependency = DependentPackage(
                        package=new_package,
                        purl=dependency.purl,
                        extracted_requirement=dependency.extracted_requirement,
                        scope=dependency.scope,
                        is_runtime=dependency.is_runtime,
                        is_optional=dependency.is_optional,
                        is_resolved=dependency.is_resolved,
                    )
                    unsaved_dependencies.append(new_dependency)

                for party in package.parties.all():
                    new_party = Party(
                        package=new_package,
                        type=party.type,
                        role=party.role,
                        name=party.name,
                        email=party.email,
                        url=party.url,
                    )
                    unsaved_parties.append(new_party)

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
