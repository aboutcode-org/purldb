#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import signal
import sys
import time

from django.db import transaction
from django.utils import timezone
from packagedcode.maven import build_filename
from packagedcode.maven import get_urls
from packagedcode.maven import _parse
from packageurl import normalize_qualifiers
from packageurl import PackageURL
import requests

from minecode.management.commands import VerboseCommand
from minecode.models import PriorityResourceURI
from minecode.utils import stringify_null_purl_fields
from packagedb.models import DependentPackage
from packagedb.models import Package
from packagedb.models import Party


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)

# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 10

MUST_STOP = False


def stop_handler(*args, **kwargs):
    """
    Signal handler to set global variable to True.
    """
    global MUST_STOP
    MUST_STOP = True


signal.signal(signal.SIGTERM, stop_handler)


class Command(VerboseCommand):
    help = 'Run a Package request queue.'

    def handle(self, *args, **options):
        """
        Get the next processable PriorityResourceURI and start the
        processing. Loops forever and sleeps a short while if there are
        no PriorityResourceURI left to process.
        """

        global MUST_STOP

        sleeping = False
        processed_counter = 0

        while True:
            if MUST_STOP:
                logger.info('Graceful exit of the request queue.')
                break

            with transaction.atomic():
                priority_resource_uri = PriorityResourceURI.objects.get_next_request()

            if not priority_resource_uri:
                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    logger.info('No more processable request, sleeping...')

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            sleeping = False

            # process request
            logger.info('Processing {}'.format(priority_resource_uri))
            process_request(priority_resource_uri.package_url)
            priority_resource_uri.processed_date = timezone.now()
            priority_resource_uri.save()
            processed_counter += 1

        return processed_counter


# TODO: use purl in uri field (?)
def process_request(package_url):
    purl = PackageURL.from_string(package_url)
    has_version = bool(purl.version)
    if has_version:
        urls = get_urls(
            namespace=purl.namespace,
            name=purl.name,
            version=purl.version,
            qualifiers=purl.qualifiers
        )
        # Get and parse POM info
        pom_url = urls['api_data_url']
        response = requests.get(pom_url)
        if not response:
            raise Exception("package does not exist on maven")

        # Create Package from POM info
        pom_contents = str(response.content)
        package = _parse(
            'maven_pom',
            'maven',
            'Java',
            text=pom_contents
        )

        # Check to see if source and binary are available
        download_url = urls['repository_download_url']
        binary_sha1_url = f'{download_url}.sha1'
        response = requests.get(binary_sha1_url)
        if response:
            create_package(package)

        # Check to see if the sources are available
        purl.qualifiers['classifier'] = 'sources'
        sources_urls = get_urls(
            namespace=purl.namespace,
            name=purl.name,
            version=purl.version,
            qualifiers=purl.qualifiers
        )
        download_url = sources_urls['repository_download_url']
        sources_sha1_url = f'{download_url}.sha1'
        response = requests.get(sources_sha1_url)
        if response:
            package.download_url = download_url
            package.repository_download_url = download_url
            create_package(package, classifier='sources')






        # if sha1 exists for a jar, we know we can create the package
        # use pom info as base and create packages for binary and source package
        # TODO: relate the two when we have PAckageRelation

        # Create Package from pom metadata and save to packagedb

        # Download artifacts for scanning
    else:
        pass


def create_package(package, extension='.jar', classifier=None):
    filename = build_filename(
        artifact_id=package.name,
        version=package.version,
        extension=extension,
        classifier=classifier,
    )
    if not package.download_url:
        download_url = package.repository_download_url
    else:
        download_url = package.download_url

    if classifier:
        package.qualifiers['classifier'] = classifier

    package_data = dict(
        filename=filename,
        release_date=package.release_date,
        type=package.type,
        namespace=package.namespace,
        name=package.name,
        version=package.version,
        qualifiers=normalize_qualifiers(package.qualifiers, encode=True),
        subpath=package.subpath,
        primary_language=package.primary_language,
        description=package.description,
        keywords=package.keywords,
        homepage_url=package.homepage_url,
        download_url=download_url,
        size=package.size,
        sha1=package.sha1,
        md5=package.md5,
        sha256=package.sha256,
        sha512=package.sha512,
        bug_tracking_url=package.bug_tracking_url,
        code_view_url=package.code_view_url,
        vcs_url=package.vcs_url,
        copyright=package.copyright,
        license_expression=package.license_expression,
        declared_license=package.declared_license,
        notice_text=package.notice_text,
        source_packages=package.source_packages
    )

    stringify_null_purl_fields(package_data)

    created_package = Package.objects.create(**package_data)
    created_package.append_to_history(
        f'New Package created from PriorityResourceURI: {download_url} via create_package().'
    )

    for party in package.parties:
        Party.objects.create(
            package=created_package,
            type=party.type,
            role=party.role,
            name=party.name,
            email=party.email,
            url=party.url,
        )

    for dependency in package.dependencies:
        DependentPackage.objects.create(
            package=created_package,
            purl=dependency.purl,
            requirement=dependency.extracted_requirement,
            scope=dependency.scope,
            is_runtime=dependency.is_runtime,
            is_optional=dependency.is_optional,
            is_resolved=dependency.is_resolved,
        )

    created_package.last_modified_date = timezone.now()
    created_package.save()
    return created_package
