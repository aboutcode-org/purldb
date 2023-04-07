#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import hashlib
import logging
import signal
import sys
import time

from django.db import transaction
from django.utils import timezone
from packagedcode.maven import get_urls
from packagedcode.maven import _parse
from packagedcode.maven import get_maven_pom
from packageurl import PackageURL
import requests

from minecode.management.commands import get_error_message
from minecode.management.commands import VerboseCommand
from minecode.management.commands.run_map import merge_or_create_package
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
            try:
                errors = process_request(priority_resource_uri)
            except Exception as e:
                errors = 'Error: Failed to process PriorityResourceURI: {}\n'.format(
                    repr(priority_resource_uri))
                errors += get_error_message(e)
            finally:
                if errors:
                    priority_resource_uri.processing_error = errors
                    logger.error(errors)
                priority_resource_uri.processed_date = timezone.now()
                priority_resource_uri.wip_date = None
                priority_resource_uri.save()
                processed_counter += 1

        return processed_counter


def get_pom_contents(namespace, name, version, qualifiers):
    """
    Return the contents of the POM file of the package described by the purl
    field arguments in a string.
    """
    # Create URLs using purl fields
    urls = get_urls(
        namespace=namespace,
        name=name,
        version=version,
        qualifiers=qualifiers
    )
    # Get and parse POM info
    pom_url = urls['api_data_url']
    response = requests.get(pom_url)
    if not response:
        return
    return str(response.content)


def get_package_sha1(package):
    """
    Return the sha1 value for `package` by checking if the sha1 file exists for
    `package` on maven and returning the contents if it does.

    If the sha1 is invalid, we download the package's JAR and calculate the sha1
    from that.
    """
    download_url = package.repository_download_url
    sha1_download_url = f'{download_url}.sha1'
    response = requests.get(sha1_download_url)
    if response.ok:
        sha1_contents = response.text.strip().split()
        sha1 = sha1_contents[0]
        sha1 = validate_sha1(sha1)
        if not sha1:
            # Download JAR and calculate sha1 if we cannot get it from the repo
            response = requests.get(download_url)
            if response:
                sha1_hash = hashlib.new('sha1', response.content)
                sha1 = sha1_hash.hexdigest()
        return sha1


def add_package_to_scan_queue(package):
    """
    Add a Package `package` to the scan queue
    """
    uri = package.download_url
    _, scannable_uri_created = ScannableURI.objects.get_or_create(
        uri=uri,
        package=package,
    )
    if scannable_uri_created:
        logger.debug(' + Inserted ScannableURI\t: {}'.format(uri))


def map_maven_package(package_url):
    """
    Add a maven `package_url` to the PackageDB.

    Return an error string if errors have occured in the process.
    """
    error = ''

    pom_contents = get_pom_contents(
        namespace=package_url.namespace,
        name=package_url.name,
        version=package_url.version,
        qualifiers=package_url.qualifiers
    )
    if not pom_contents:
        msg = f'Package does not exist on maven: {package_url}'
        error += msg + '\n'
        logger.error(msg)
        return error

    package = _parse(
        'maven_pom',
        'maven',
        'Java',
        text=pom_contents
    )

    # Create Parent Package, if available
    parent_package = None
    pom = get_maven_pom(text=pom_contents)
    if (
        pom.parent
        and pom.parent.group_id
        and pom.parent.artifact_id
        and pom.parent.version.version
    ):
        parent_namespace = pom.parent.group_id
        parent_name = pom.parent.artifact_id
        parent_version = str(pom.parent.version.version)
        parent_pom_contents = get_pom_contents(
            namespace=parent_namespace,
            name=parent_name,
            version=parent_version,
            qualifiers={}
        )
        if not parent_pom_contents:
            parent_purl = PackageURL(
                namespace=parent_namespace,
                name=parent_name,
                version=parent_version,
            )
            logger.debug(f'\tParent POM does not exist on maven {parent_purl}')
        else:
            parent_package = _parse(
                'maven_pom',
                'maven',
                'Java',
                text=parent_pom_contents
            )

    if parent_package:
        check_fields = (
            'license_expression',
            'homepage_url',
            'parties',
        )
        for field in check_fields:
            # If `field` is empty on the package we're looking at, populate
            # those fields with values from the parent package.
            if not getattr(package, field):
                value = getattr(parent_package, field)
                setattr(package, field, value)

    # If sha1 exists for a jar, we know we can create the package
    # Use pom info as base and create packages for binary and source package

    # Check to see if binary is available
    db_package = None
    sha1 = get_package_sha1(package)
    if sha1:
        package.sha1 = sha1
        package.download_url = package.repository_download_url
        db_package, _, _, _ = merge_or_create_package(package, visit_level=0)
    else:
        msg = f'Failed to retrieve JAR: {package_url}'
        error += msg + '\n'
        logger.error(msg)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(db_package)

    return db_package, error


def process_request(priority_resource_uri):
    """
    Process `priority_resource_uri` containing a maven Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from maven and
    using it to create a new PackageDB entry. The package is then added to the
    scan queue afterwards. We also get the Package information for the
    accompanying source package and add it to the PackageDB and scan queue, if
    available.
    """
    purl_str = priority_resource_uri.uri
    package_url = PackageURL.from_string(purl_str)
    has_version = bool(package_url.version)
    error = ''
    if has_version:
        package, emsg = map_maven_package(package_url)
        if emsg:
            error += emsg

        source_package_url = package_url
        source_package_url.qualifiers['classifier'] = 'sources'
        source_package, emsg = map_maven_package(source_package_url)
        if emsg:
            error += emsg

        if package and source_package:
            make_relationship(
                from_package=source_package,
                to_package=package,
                relationship=PackageRelation.Relationship.SOURCE_PACKAGE
            )

        return error
    else:
        pass


def make_relationship(
    from_package, to_package, relationship
):
    return PackageRelation.objects.create(
        from_package=from_package,
        to_package=to_package,
        relationship=relationship,
    )

def validate_sha1(sha1):
    """
    Validate a `sha1` string.

    Return `sha1` if it is valid, None otherwise.
    """
    if sha1 and len(sha1) != 40:
        logger.warning(
            f'Invalid SHA1 length ({len(sha1)}): "{sha1}": SHA1 ignored!'
        )
        sha1 = None
    return sha1
