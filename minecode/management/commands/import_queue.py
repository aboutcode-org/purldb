#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from dateutil.parser import parse as dateutil_parse
import logging
import signal
import sys
import time

import requests

from django.db import transaction
from django.utils import timezone
from packageurl import PackageURL

from minecode.management.commands import get_error_message
from minecode.management.commands import VerboseCommand
from minecode.models import ImportableURI
from minecode.visitors.maven import get_artifact_links
from minecode.visitors.maven import get_classifier_from_artifact_url
from minecode.visitors.maven import collect_links_from_text
from minecode.visitors.maven import filter_only_directories
from minecode.visitors.maven import get_artifact_sha1
from minecode.model_utils import merge_or_create_package
from packagedcode.models import PackageData
from minecode.visitors.maven import determine_namespace_name_version_from_url


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
                importable_uri = ImportableURI.objects.get_next_request()

            if not importable_uri:
                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    logger.info('No more processable request, sleeping...')

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            sleeping = False

            # process request
            logger.info('Processing {}'.format(importable_uri))
            try:
                errors = process_request(importable_uri)
            except Exception as e:
                errors = 'Error: Failed to process ImportableURI: {}\n'.format(
                    repr(importable_uri))
                errors += get_error_message(e)
            finally:
                if errors:
                    importable_uri.processing_error = errors
                    logger.error(errors)
                importable_uri.processed_date = timezone.now()
                importable_uri.wip_date = None
                importable_uri.save()
                processed_counter += 1

        return processed_counter


def process_request(importable_uri):
    uri = importable_uri.uri
    uri = uri.rstrip('/')
    data = importable_uri.data
    if not data:
        # collect data again if we don't have it
        response = requests.get(uri)
        if response:
            data = requests.text

    purl = importable_uri.package_url
    if purl:
        package_url = PackageURL.from_string(purl)
        namespace = package_url.namespace
        name = package_url.name
    else:
        namespace, name, _ = determine_namespace_name_version_from_url(uri)

    timestamps_by_directory_links = collect_links_from_text(data, filter_only_directories)
    # Go into each version directory
    for directory_link in timestamps_by_directory_links.keys():
        version = directory_link.rstrip('/')
        version_page_url = f'{uri}/{version}'
        timestamps_by_artifact_links = get_artifact_links(version_page_url)
        for artifact_link, timestamp in timestamps_by_artifact_links.items():
            sha1 = get_artifact_sha1(artifact_link)
            classifier = get_classifier_from_artifact_url(artifact_link, version_page_url, name, version)
            qualifiers = None
            if classifier:
                qualifiers = f'classifier={classifier}'
            release_date = dateutil_parse(timestamp)
            package_data = PackageData(
                type='maven',
                namespace=namespace,
                name=name,
                version=version,
                qualifiers=qualifiers,
                download_url=artifact_link,
                sha1=sha1,
                release_date=release_date,
            )
            package, created, merged, map_error = merge_or_create_package(
                scanned_package=package_data,
                visit_level=50
            )
            if created:
                logger.info(f'Created package {package}')
            if merged:
                logger.info(f'Updated package {package}')
            if map_error:
                logger.error(f'Error encountered: {map_error}')
                importable_uri.processing_error = map_error
                importable_uri.save()
