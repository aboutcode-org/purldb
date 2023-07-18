#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

import logging
import signal
import sys

from django.db import transaction

from packagedcode.utils import combine_expressions

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ExactFileIndex
from minecode.management import scanning
from minecode.management.commands import get_error_message
from minecode.models import ScannableURI
from minecode.model_utils import merge_or_create_resource


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
    def process_scan(cls, scannable_uri, get_scan_info_save_loc='', get_scan_data_save_loc='', **kwargs):
        """
        Process a ScannableURI based on its status.
        - For requested but not completed scans, check remote status and
          update status and timestamps accordingly.
        - For completed scans, fetch the scan, then procpythess the scan results
          to update the PackageDB as needed. Update status and timestamps accordingly
        """
        logger.info('Checking or processing scan for URI: {}'.format(scannable_uri))

        scan_info = scanning.get_scan_info(
            scannable_uri.scan_uuid,
            api_url=cls.api_url,
            api_auth_headers=cls.api_auth_headers,
            get_scan_info_save_loc=get_scan_info_save_loc
        )

        if scannable_uri.scan_status in (ScannableURI.SCAN_SUBMITTED, ScannableURI.SCAN_IN_PROGRESS):
            scannable_uri.scan_status = get_scan_status(scan_info)
        elif scannable_uri.scan_status in (ScannableURI.SCAN_COMPLETED,):
            scan_index_errors = []
            try:
                logger.info('Indexing scanned files for URI: {}'.format(scannable_uri))

                package = scannable_uri.package
                input_size = scan_info.size
                if input_size:
                    computed_timeout = ((input_size / 1000000) / 2) * 60
                    timeout = max(computed_timeout, scanning.REQUEST_TIMEOUT)
                else:
                    timeout = scanning.REQUEST_TIMEOUT
                scan_data = scanning.get_scan_data(
                    scannable_uri.scan_uuid,
                    api_url=cls.api_url,
                    api_auth_headers=cls.api_auth_headers,
                    timeout=timeout,
                    get_scan_data_save_loc=get_scan_data_save_loc
                )
                scan_index_errors.extend(index_package_files(package, scan_data))

                summary = scanning.get_scan_summary(
                    scannable_uri.scan_uuid,
                    api_url=cls.api_url,
                    api_auth_headers=cls.api_auth_headers,
                    get_scan_data_save_loc=get_scan_data_save_loc
                )

                other_license_expressions = summary.get('other_license_expressions', [])
                other_license_expressions = [l['value'] for l in other_license_expressions if l['value']]
                other_license_expression = combine_expressions(other_license_expressions)

                copyright = ''
                declared_holder = summary.get('declared_holder')
                if declared_holder:
                    copyright = f'Copyright (c) {declared_holder}'

                values_by_updateable_fields = {
                    'sha1': scan_info.sha1,
                    'sha256': scan_info.sha256,
                    'sha512': scan_info.sha512,
                    'summary': summary,
                    'declared_license_expression': summary.get('declared_license_expression'),
                    'other_license_expression': other_license_expression,
                    'copyright': copyright,
                }

                updated_fields = []
                for field, value in values_by_updateable_fields.items():
                    p_val = getattr(package, field)
                    if not p_val and value:
                        setattr(package, field, value)
                        updated_fields.append(field)

                if updated_fields:
                    updated_fields_str = ', '.join(updated_fields)
                    package.append_to_history(f'Updated values of fields: {updated_fields_str}')
                    package.save()

                scannable_uri.scan_status = ScannableURI.SCAN_INDEXED
            except Exception as e:
                error_message = str(e) + '\n'
                # TODO: We should rerun the specific indexers that have failed
                if scan_index_errors:
                    error_message += '\n'.join(scan_index_errors)
                scannable_uri.index_error
                scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED

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
        for resource in scan_data.get('files', []):
            r, _, _ = merge_or_create_resource(package, resource)
            path = r.path
            sha1 = r.sha1
            if sha1:
                _, _ = ExactFileIndex.index(
                    sha1=sha1,
                    package=package
                )

            resource_extra_data = resource.get('extra_data', {})
            directory_content_fingerprint = resource_extra_data.get('directory_content', '')
            directory_structure_fingerprint = resource_extra_data.get('directory_structure', '')

            if directory_content_fingerprint:
                _, _ = ApproximateDirectoryContentIndex.index(
                    directory_fingerprint=directory_content_fingerprint,
                    resource_path=path,
                    package=package,
                )
            if directory_structure_fingerprint:
                _, _ = ApproximateDirectoryStructureIndex.index(
                    directory_fingerprint=directory_structure_fingerprint,
                    resource_path=path,
                    package=package,
                )

    except Exception as e:
        msg = get_error_message(e)
        scan_index_errors.append(msg)
        logger.error(msg)

    return scan_index_errors
