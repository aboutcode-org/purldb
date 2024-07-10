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
from minecode.management.commands import VerboseCommand
from packagedb.management.commands.update_maven_download_urls import check_download_url
from packagedb.models import Package
from packagedcode.maven import get_urls, build_filename
from packageurl import PackageURL

DEFAULT_TIMEOUT = 30

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

session = Session()
session.mount('https://', HTTPAdapter(max_retries=Retry(10)))
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
}


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
        maven_packages = Package.objects.filter(type='maven', sha1__is_null=False)
        maven_packages_count = maven_packages.count()
        logger.info(f'Checking {maven_packages_count:,} Maven Package PackageURL values')
        packages_to_delete = []
        unsaved_packages = []

        processed_packages_count = 0
        for i, package in enumerate(MemorySavingQuerysetIterator(maven_packages)):
            matched_artifacts = query_sha1_on_maven(package.sha1)
            if not matched_artifacts:
                # Remove this package from the database because it's not on maven
                packages_to_delete.append(package)
            for artifact in matched_artifacts:
                artifact_namespace = artifact.namespace
                artifact_name = artifact.name
                artifact_version = artifact.version
                artifact_qualifiers = artifact.qualifiers

                package_different_case = Package.objects.get_or_none(
                    namespace__iexact=artifact_namespace,
                    name__iexact=artifact_name,
                    version__iexact=artifact_version,
                    artifact_qualifiers__iexact=artifact_qualifiers,
                )

                # check to see if the artifact matches the current package
                if (
                    package.namespace == artifact_namespace
                    and package.name == artifact_name
                    and package.version == artifact_version
                    and package.qualifiers == artifact_qualifiers
                ):
                    # check download url
                    if check_download_url(package.download_url):
                        # Continue if it resolves
                        continue
                    else:
                        package.download_url = artifact.download_url
                        package.release_date = artifact.release_date
                        package.save()
                elif package_different_case:
                    package_different_case.namespace = artifact_namespace
                    package_different_case.name = artifact_name
                    package_different_case.version = artifact_version
                    package_different_case.qualifiers = artifact_qualifiers
                    package_different_case.download_url = artifact.download_url
                    package_different_case.release_date = artifact.release_date
                    package_different_case.repository_homepage_url = artifact.repository_homepage_url
                    package_different_case.repository_download_url = artifact.repository_download_url
                    package_different_case.api_data_url = artifact.api_data_url
                    package_different_case.save()
