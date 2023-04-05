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
from packagedcode.maven import get_urls
from packagedcode.maven import _parse
from packageurl import PackageURL
import requests

from minecode.management.commands import VerboseCommand
from minecode.management.commands.run_map import merge_or_create_package
from minecode.management.commands.process_scans import get_scan_status
from minecode.management.commands.process_scans import index_package_files
from minecode.management.scanning import submit_scan
from minecode.management.scanning import get_scan_info
from minecode.management.scanning import get_scan_data
from minecode.models import PriorityResourceURI
from minecode.models import ScannableURI
from packagedb.models import PackageRelation


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
            errors = process_request(priority_resource_uri.uri)
            if errors:
                priority_resource_uri.processing_error = errors
            priority_resource_uri.processed_date = timezone.now()
            priority_resource_uri.save()
            processed_counter += 1

        return processed_counter


def process_request(package_url):
    """
    TODO: move this to Maven visitor/mapper
    """
    purl = PackageURL.from_string(package_url)
    has_version = bool(purl.version)
    error = ''
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
            msg = 'Package does not exist on maven: ' + repr(package_url)
            error += msg + '\n'
            logger.error(msg)
            return error

        # Create Package from POM info
        pom_contents = str(response.content)
        package = _parse(
            'maven_pom',
            'maven',
            'Java',
            text=pom_contents
        )

        # If sha1 exists for a jar, we know we can create the package
        # Use pom info as base and create packages for binary and source package
        # TODO: relate the two when we have PackageRelation

        # Check to see if source and binary are available
        download_url = urls['repository_download_url']
        binary_sha1_url = f'{download_url}.sha1'
        response = requests.get(binary_sha1_url)
        if response.ok:
            # Create Package for binary package, if available
            package.sha1 = response.text.strip()
            package.download_url = download_url
            binary_package, _, _, _ = merge_or_create_package(package, visit_level=0)
        else:
            msg = 'Failed to retrieve binary JAR: ' + repr(package_url)
            error += msg + '\n'
            logger.error(msg)

        # Submit packages for scanning
        if binary_package:
            uri = binary_package.download_url
            _, scannable_uri_created = ScannableURI.objects.get_or_create(
                uri=uri,
                package=binary_package,
            )
            if scannable_uri_created:
                logger.debug(' + Inserted ScannableURI\t: {}'.format(uri))

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
        if response.ok:
            # Create Package for source package, if available
            package.sha1 = response.text.strip()
            package.download_url = download_url
            package.repository_download_url = download_url
            package.qualifiers['classifier'] = 'sources'
            source_package, _, _, _ = merge_or_create_package(package, visit_level=0)
        else:
            msg = 'Failed to retrieve sources JAR: ' + repr(package_url)
            error += msg + '\n'
            logger.error(msg)

        if source_package:
            uri = source_package.download_url
            _, scannable_uri_created = ScannableURI.objects.get_or_create(
                uri=uri,
                package=source_package,
            )
            if scannable_uri_created:
                logger.debug(' + Inserted ScannableURI\t: {}'.format(uri))

        if source_package and binary_package:
            make_relationship(
                from_package=source_package,
                to_package=binary_package,
                relationship=PackageRelation.Relationship.SOURCE_PACKAGE
            )

        return error
    else:
        pass


def make_relationship(
    from_package, to_package, relationship
):
    """
    from scio
    """
    return PackageRelation.objects.create(
        from_package=from_package,
        to_package=to_package,
        relationship=relationship,
    )

def validate_sha1(sha1):
    if sha1 and len(sha1) != 40:
        logger.warning(
            f'Invalid SHA1 length ({len(sha1)}): "{sha1}": SHA1 ignored!'
        )
        sha1 = None
    return sha1
