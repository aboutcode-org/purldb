#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import copy
import logging
import sys

from minecode.management.commands import VerboseCommand
from packagedb.models import Package, DependentPackage, Party, Resource
from matchcode.models import ApproximateDirectoryContentIndex, ApproximateDirectoryStructureIndex

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


# This is from https://stackoverflow.com/questions/4856882/limiting-memory-use-in-a-large-django-queryset/5188179#5188179
class MemorySavingQuerysetIterator(object):

    def __init__(self,queryset,max_obj_num=1000):
        self._base_queryset = queryset
        self._generator = self._setup()
        self.max_obj_num = max_obj_num

    def _setup(self):
        for i in range(0,self._base_queryset.count(),self.max_obj_num):
            # By making a copy of of the queryset and using that to actually access
            # the objects we ensure that there are only `max_obj_num` objects in
            # memory at any given time
            smaller_queryset = copy.deepcopy(self._base_queryset)[i:i+self.max_obj_num]
            logger.debug('Grabbing next %s objects from DB' % self.max_obj_num)
            for obj in smaller_queryset.iterator():
                yield obj

    def __iter__(self):
        return self._generator

    def next(self):
        return self._generator.next()


class Command(VerboseCommand):
    def handle(self, *args, **options):
        packages = Package.objects.using('minecode').all()
        package_count = packages.count()
        unsaved_packages = []
        unsaved_dependencies = []
        unsaved_parties = []
        unsaved_directory_content_fingerprints = []
        unsaved_directory_structure_fingerprints = []
        unsaved_resources = []

        print(f"Copying {package_count:,} Packages from the 'minecode' database to the 'default' database")
        i = 0
        skipped_packages_count = 0
        for package in MemorySavingQuerysetIterator(packages):
            if Package.objects.filter(download_url=package.download_url).exists():
                skipped_packages_count += 1
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
                ApproximateDirectoryContentIndex.objects.bulk_create(
                    unsaved_directory_content_fingerprints
                )
                ApproximateDirectoryStructureIndex.objects.bulk_create(
                    unsaved_directory_structure_fingerprints
                )
                Resource.objects.bulk_create(
                    unsaved_resources
                )
                unsaved_packages = []
                unsaved_dependencies = []
                unsaved_parties = []
                unsaved_directory_content_fingerprints = []
                unsaved_directory_structure_fingerprints = []
                unsaved_resources = []
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

                for directory_content_fingerprint in package.approximatedirectorycontentindex_set.all():
                    new_directory_content_fingerprint = ApproximateDirectoryContentIndex(
                        indexed_elements_count=directory_content_fingerprint.indexed_elements_count,
                        chunk1=directory_content_fingerprint.chunk1,
                        chunk2=directory_content_fingerprint.chunk2,
                        chunk3=directory_content_fingerprint.chunk3,
                        chunk4=directory_content_fingerprint.chunk4,
                        package=package,
                        path=directory_content_fingerprint.path,
                    )
                    unsaved_directory_content_fingerprints(new_directory_content_fingerprint)

                for directory_structure_fingerprint in package.p.approximatedirectorystructureindex_set.all():
                    new_directory_structure_fingerprint = ApproximateDirectoryStructureIndex(
                        indexed_elements_count=directory_structure_fingerprint.indexed_elements_count,
                        chunk1=directory_structure_fingerprint.chunk1,
                        chunk2=directory_structure_fingerprint.chunk2,
                        chunk3=directory_structure_fingerprint.chunk3,
                        chunk4=directory_structure_fingerprint.chunk4,
                        package=package,
                        path=directory_structure_fingerprint.path,
                    )
                    unsaved_directory_structure_fingerprints(new_directory_structure_fingerprint)

                for resource in package.resources.all():
                    new_resource = Resource(
                        package=package,
                        path=resource.path,
                        name=resource.name,
                        extension=resource.extension,
                        size=resource.size,
                        mime_type=resource.mime_type,
                        file_type=resource.file_type,
                        programming_language=resource.programming_language,
                        is_binary=resource.is_binary,
                        is_text=resource.is_text,
                        is_archive=resource.is_archive,
                        is_key_file=resource.is_key_file,
                        is_media=resource.is_media,
                        is_file=resource.is_file,
                        md5=resource.md5,
                        sha1=resource.sha1,
                        sha256=resource.sha256,
                        sha512=resource.sha512,
                        git_sha1=resource.git_sha1,
                        detected_license_expression=resource.detected_license_expression,
                        detected_license_expression_spdx=resource.detected_license_expression_spdx,
                        license_detections=resource.license_detections,
                        license_clues=resource.license_clues,
                        percentage_of_license_text=resource.percentage_of_license_text,
                        copyrights=resource.copyrights,
                        holders=resource.holders,
                        authors=resource.authors,
                        package_data=resource.package_data,
                        emails=resource.emails,
                        urls=resource.urls,
                        extra_data=resource.extra_data,
                    )
                    unsaved_resources.append(new_resource)

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
            ApproximateDirectoryContentIndex.objects.bulk_create(
                unsaved_directory_content_fingerprints
            )
            ApproximateDirectoryStructureIndex.objects.bulk_create(
                unsaved_directory_structure_fingerprints
            )
            Resource.objects.bulk_create(
                unsaved_resources
            )
            unsaved_packages = []
            unsaved_dependencies = []
            unsaved_parties = []
            unsaved_directory_content_fingerprints = []
            unsaved_directory_structure_fingerprints = []
            unsaved_resources = []
            print(f"  {i:,} / {package_count:,} saved")

        print(f"{i:,} Packages saved, {skipped_packages_count:,} Packages skipped")
