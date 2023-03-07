#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from collections import OrderedDict
import json
import logging
import os
import signal
import sys

from django.db import transaction

from license_expression import Licensing
from commoncode.resource import VirtualCodebase

from matchcode.indexing import index_directory_fingerprints
from minecode.management import scanning
from minecode.management.commands import get_error_message
from minecode.models import ScannableURI
from packagedb.models import Resource

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(scanning.ScanningCommand):

    logger = logger

    help = ('Check scancode.io requested scans for status then fetch and process '
            'completed scans for indexing and updates.')

    def handle(self, *args, **options):
        logger.setLevel(self.get_verbosity(**options))
        scanning.ScanningCommand.handle(self, *args, **options)

    @classmethod
    def get_next_uri(self):
        with transaction.atomic():
            scannable_uri = ScannableURI.objects.get_next_processable()
        return scannable_uri

    @classmethod
    def process_scan(cls, scannable_uri, **kwargs):
        """
        Process a ScannableURI based on its status.
        - For requested but not completed scans, check remote status and
          update status and timestamps accordingly.
        - For completed scans, fetch the scan, then procpythess the scan results
          to update the PackageDB as needed. Update status and timestamps accordingly
        """
        logger.info('Checking or processing scan for URI: {}'.format(scannable_uri))

        scan_info = scanning.get_scan_info(scannable_uri.scan_uuid, api_url=cls.api_url, api_auth_headers=cls.api_auth_headers)

        if scannable_uri.scan_status in (ScannableURI.SCAN_SUBMITTED, ScannableURI.SCAN_IN_PROGRESS):
            scannable_uri.scan_status = get_scan_status(scan_info)
        elif scannable_uri.scan_status in (ScannableURI.SCAN_COMPLETED,):
            logger.info('Indexing scanned files for URI: {}'.format(scannable_uri))

            package = scannable_uri.package
            scan_data = scanning.get_scan_data(
                scannable_uri.scan_uuid, api_url=cls.api_url, api_auth_headers=cls.api_auth_headers)
            scan_index_errors = index_package_files(package, scan_data)
            # TODO: We should rerun the specific indexers that have failed
            if scan_index_errors:
                scannable_uri.index_error = '\n'.join(scan_index_errors)
                scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
            else:
                scannable_uri.scan_status = ScannableURI.SCAN_INDEXED

        scannable_uri.wip_date = None
        scannable_uri.save()


# support graceful death when used as a service
signal.signal(signal.SIGTERM, Command.stop_handler)


def get_scan_status(scan_object):
    """
    Return a ScannableURI status from scan_object Scan
    """
    if scan_object.not_started or scan_object.queued:
        scan_status = ScannableURI.SCAN_SUBMITTED
    elif scan_object.running:
        scan_status = ScannableURI.SCAN_IN_PROGRESS
    elif scan_object.failure or scan_object.stopped or scan_object.stale:
        scan_status = ScannableURI.SCAN_FAILED
    elif scan_object.success:
        scan_status = ScannableURI.SCAN_COMPLETED
    else:
        # TODO: Consider not raising an exception
        raise Exception('Unknown scancode.io status')
    return scan_status


def update_package_checksums(package, scan_object):
    """
    Create a new Resource entry for `package` Package if its checksums have been updated

    Return a list of scan error messages
    """
    scan_index_errors = []
    try:
        updated = _update_package_checksums(package, scan_object)
    except Exception as e:
        msg = get_error_message(e)
        scan_index_errors.append(msg)
        logger.error(msg)
    return scan_index_errors


def _update_package_checksums(package, scan_object):
    """
    Update and save `package` Package checksums with data from `scan_object` Scan.

    Return True if the package was updated.
    """
    updated = False
    if ((package.sha1 and package.sha1 != scan_object.sha1) or
            (package.md5 and package.md5 != scan_object.md5) or
            (package.size and package.size != scan_object.size)):
        raise Exception(
            'Inconsistent checksum or size collected from scan uuid: {} for Package {}'
            .format(scan_object.uuid, package.uuid)
        )

    if not package.sha1:
        package.sha1 = scan_object.sha1
        updated = True
    if not package.md5:
        package.md5 = scan_object.md5
        updated = True
    if not package.size:
        package.size = scan_object.size
        updated = True
    if updated:
        package.save()
    return updated


def index_package_files(package, scan_data):
    """
    Index scan data for `package` Package.

    Return a list of scan index errors messages
    """
    scan_index_errors = []
    try:
        resource_attributes = dict()
        vc = VirtualCodebase(
            location=scan_data,
            resource_attributes=resource_attributes
        )
        for resource in vc.walk(topdown=True):
            path = resource.path
            sha1 = resource.sha1
            size = resource.size
            md5 = resource.md5
            is_file = resource.type == 'file'

            copyrights = []
            for copyright_mapping in resource.copyrights:
                copyright = copyright_mapping.get('copyright')
                if not copyright:
                    continue
                copyrights.append(copyright)
            copyrights = '\n'.join(copyrights)

            combined_license_expression = combine_expressions(resource.license_expressions)
            if combined_license_expression:
                license_expression = str(Licensing().parse(combined_license_expression).simplify())
            else:
                license_expression = None

            # TODO: Determine what extra_data to keep

            r, _ = Resource.objects.get_or_create(
                package=package,
                path=path,
                size=size,
                sha1=sha1,
                md5=md5,
                copyright=copyrights,
                license_expression=license_expression,
                is_file=is_file,
            )
        _, _ = index_directory_fingerprints(vc, package)

    except Exception as e:
        msg = get_error_message(e)
        scan_index_errors.append(msg)
        logger.error(msg)

    return scan_index_errors


# TODO: Remove this when scancode-toolkit is upgraded. The current version of
# scancode-toolkit in Minecode does not have this function
# TODO: from packagedcode.utils import combine_expressions
def combine_expressions(expressions, relation='AND', licensing=Licensing()):
    """
    Return a combined license expression string with relation, given a list of
    license expressions strings.

    For example:
    >>> a = 'mit'
    >>> b = 'gpl'
    >>> combine_expressions([a, b])
    'mit AND gpl'
    >>> assert 'mit' == combine_expressions([a])
    >>> combine_expressions([])
    >>> combine_expressions(None)
    >>> combine_expressions(('gpl', 'mit', 'apache',))
    'gpl AND mit AND apache'
    """
    if not expressions:
        return

    if not isinstance(expressions, (list, tuple)):
        raise TypeError(
            'expressions should be a list or tuple and not: {}'.format(
                type(expressions)))

    # Remove duplicate element in the expressions list
    expressions = list(OrderedDict((x, True) for x in expressions).keys())

    if len(expressions) == 1:
        return expressions[0]

    expressions = [licensing.parse(le, simple=True) for le in expressions]
    if relation == 'OR':
        return str(licensing.OR(*expressions))
    else:
        return str(licensing.AND(*expressions))
