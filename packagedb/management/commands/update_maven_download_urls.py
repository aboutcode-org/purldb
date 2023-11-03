#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from dateutil.parser import parse as dateutil_parse
import copy
import logging
import sys

from django.db import transaction

from urllib3.util import Retry
from requests import Session
from requests.adapters import HTTPAdapter
import requests

from minecode.visitors.maven import collect_links_from_text
from minecode.visitors.maven import filter_for_artifacts
from packagedcode.maven import get_urls, build_filename
from minecode.management.commands import VerboseCommand
from packagedb.models import Package
from packagedcode.maven import get_urls
from packageurl import PackageURL

DEFAULT_TIMEOUT = 30

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

session = Session()
session.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
}
session.mount('https://', HTTPAdapter(max_retries=Retry(10)))


def get_timestamps_by_links(package_version_page_url):
    timestamps_by_links = {}
    response = requests.get(package_version_page_url)
    if response:
        timestamps_by_links = collect_links_from_text(response.text, filter=filter_for_artifacts)
        timestamps_by_links = {
            link: dateutil_parse(timestamp) for link, timestamp in timestamps_by_links.items()
        }
    return timestamps_by_links


class MavenArtifact(object):
    def __init__(self, namespace, name, version, qualifiers='', ec=[]):
        type = 'maven'
        self.type = type
        self.namespace = namespace
        self.name = name
        self.version = version
        self.qualifiers = qualifiers
        self.package_url = PackageURL(
            type=type,
            namespace=namespace,
            name=name,
            version=version,
            qualifiers=qualifiers
        )
        urls = get_urls(
            namespace=namespace,
            name=name,
            version=version,
            qualifiers=self.package_url.qualifiers,
        )
        self.download_url = urls['repository_download_url']
        self.repository_homepage_url = urls['repository_homepage_url']
        self.api_data_url = urls['api_data_url']

        qualifiers_mapping = self.package_url.qualifiers
        filename = build_filename(
            artifact_id=name,
            version=version,
            extension=qualifiers_mapping.get('type') or 'jar',
            classifier=qualifiers_mapping.get('classifier'),
        )
        timestamps_by_links = get_timestamps_by_links(self.repository_homepage_url)
        self.release_date = timestamps_by_links.get(filename)
        self.related_artifacts = list(
            self._populate_related_artifacts(
                namespace=namespace,
                name=name,
                version=version,
                ec=ec,
            )
        )

    @classmethod
    def _populate_related_artifacts(cls, namespace, name, version, ec):
        filtered_ec = [entry for entry in ec if not entry.startswith('.')]
        for entry in filtered_ec:
            _, ending = entry.split('-')
            split_ending = ending.split('.')
            classifier = None
            if len(split_ending) > 0:
                classifier = split_ending[0]
                qualifiers = f'classifier={classifier}'
                yield cls(
                    namespace=namespace,
                    name=name,
                    version=version,
                    qualifiers=qualifiers,
                )


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


def check_download_url(url, timeout=DEFAULT_TIMEOUT):
    """Return True if `url` is resolvable and accessable"""
    if not url:
        return
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.ok
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"[Exception] {exception}")
        return False


def query_sha1_on_maven(sha1, timeout=DEFAULT_TIMEOUT):
    maven_api_search_url = f'https://search.maven.org/solrsearch/select?q=1:{sha1}'
    try:
        response = session.get(maven_api_search_url, timeout=timeout)
        response.raise_for_status()
    except (requests.RequestException, ValueError, TypeError) as exception:
        logger.debug(f"[Exception] {exception}")
        return False
    if not response.ok:
        return f"API query failed for: {maven_api_search_url}"
    contents = response.json()
    resp = contents.get('response', {})
    matched_artifacts = []
    if resp.get('numFound', 0) > 0:
        for matched_artifact in resp.get('docs', []):
            namespace = matched_artifact.get('g', '')
            name = matched_artifact.get('a', '')
            version = matched_artifact.get('v', '')
            ec = matched_artifact.get('ec', [])
            if not namespace and name and version:
                continue
            matched_artifacts.append(
                MavenArtifact(
                    namespace=namespace,
                    name=name,
                    version=version,
                    ec=ec,
                )
            )
    return matched_artifacts


class Command(VerboseCommand):
    help = 'Update maven Package download_url values'

    def handle(self, *args, **options):
        maven_packages = Package.objects.filter(type='maven')
        maven_packages_count = maven_packages.count()
        logger.info(f'Checking {maven_packages_count:,} Maven Package download URLs')
        packages_to_delete = []
        unsaved_packages = []
        unsaved_packages_from_sha1_lookup = []
        processed_packages_count = 0
        for i, package in enumerate(MemorySavingQuerysetIterator(maven_packages)):
            if not i % 1000:
                logger.info(f'Checked {i:,} / {maven_packages_count:,} Maven Package download URLs')
            if not i % 2000:
                if unsaved_packages:
                    with transaction.atomic():
                        Package.objects.bulk_update(
                            objs=unsaved_packages,
                            fields=[
                                'download_url',
                            ]
                        )
                    processed_packages_count += unsaved_packages.count()
                    unsaved_packages = []
                if unsaved_packages_from_sha1_lookup:
                    with transaction.atomic():
                        Package.objects.bulk_update(
                            objs=unsaved_packages_from_sha1_lookup,
                            fields=[
                                'namespace',
                                'name',
                                'version',
                                'download_url',
                                'release_date',
                                'repository_homepage_url',
                                'repository_download_url',
                                'api_data_url',
                            ]
                        )
                    processed_packages_count += unsaved_packages_from_sha1_lookup.count()
                    unsaved_packages_from_sha1_lookup = []
                logger.info(f'Updated {processed_packages_count:,} Maven Packages')
            # If the package's download URL is not valid, then we update it
            if not check_download_url(package.download_url):
                package_url = PackageURL(
                    type=package.type,
                    namespace=package.namespace,
                    name=package.name,
                    version=package.version,
                    qualifiers=package.qualifiers,
                )
                urls = get_urls(
                    namespace=package_url.namespace,
                    name=package_url.name,
                    version=package_url.version,
                    qualifiers=package_url.qualifiers,
                )
                generated_download_url = urls['repository_download_url']
                if Package.objects.filter(download_url=generated_download_url).exists():
                    # This download url already exists in the database, we should just remove this record.
                    packages_to_delete.append(package)
                    logger.info(f'Deleting {package.package_uid} - already exists in database')
                elif check_download_url(generated_download_url):
                    package.download_url = generated_download_url
                    unsaved_packages.append(package)
                    logger.info(f'Updated download_url for {package.package_uid}')
                else:
                    # fix purl values
                    # look up package sha1 on maven
                    matched_artifacts = query_sha1_on_maven(package.sha1)
                    if not matched_artifacts:
                        packages_to_delete.append(package)
                        logger.info(f'Deleting {package.package_uid} - does not exist on Maven')
                    for artifact in matched_artifacts:
                        if (
                            package.namespace.lower() == artifact.namespace.lower()
                            and package.name.lower() == artifact.name.lower()
                            and package.version.lower() == artifact.version.lower()
                        ):
                            if Package.objects.filter(download_url=artifact.download_url).exists():
                                packages_to_delete.append(package)
                                logger.info(f'Deleting {package.package_uid} - already exists in database')
                            else:
                                package.namespace = artifact.namespace
                                package.name = artifact.name
                                package.version = artifact.version
                                package.download_url = artifact.download_url
                                package.release_date = artifact.release_date
                                package.repository_homepage_url = artifact.repository_homepage_url
                                package.repository_download_url = artifact.download_url
                                package.api_data_url = artifact.api_data_url
                                unsaved_packages_from_sha1_lookup.append(package)
                                processed_packages_count += 1
                                logger.info(
                                    f'Updated version for {package.package_uid}:\n'
                                    f'\tversion: {package.version}'
                                )
                            break
                    else:
                        logger.info(f'Cannot update PackageURL values for {package.package_uid}')

        if unsaved_packages:
            with transaction.atomic():
                Package.objects.bulk_update(
                    objs=unsaved_packages,
                    fields=[
                        'download_url',
                    ]
                )
            processed_packages_count += unsaved_packages.count()
            unsaved_packages = []

        if unsaved_packages_from_sha1_lookup:
            with transaction.atomic():
                Package.objects.bulk_update(
                    objs=unsaved_packages_from_sha1_lookup,
                    fields=[
                        'namespace',
                        'name',
                        'version',
                        'download_url',
                        'release_date',
                        'repository_homepage_url',
                        'repository_download_url',
                        'api_data_url',
                    ]
                )
            processed_packages_count += unsaved_packages_from_sha1_lookup.count()
            unsaved_packages_from_sha1_lookup = []

        logger.info(f'Updated {processed_packages_count:,} Maven Packages')

        if packages_to_delete:
            pks = [p.pk for p in packages_to_delete]
            with transaction.atomic():
                Package.objects.filter(pk__in=pks).delete()
            logger.info(f'Deleted {pks.count():,} duplicate/invalid Maven Packages')
