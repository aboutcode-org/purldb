#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#
from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ExactFileIndex
from minecode.management.commands import get_error_message
import logging
import sys
from minecode.model_utils import merge_or_create_resource
from packagedcode.utils import combine_expressions
from licensedcode.cache import build_spdx_license_expression
import traceback
from minecode.models import ScannableURI

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def index_package_files(package, scan_data, reindex=False):
    """
    Index scan data for `package` Package.

    Return a list of scan index errors messages

    If `reindex` is True, then all fingerprints related to `package` will be
    deleted and recreated from `scan_data`.
    """
    if reindex:
        logger.info(f'Deleting fingerprints and Resources related to {package.package_url}')
        package.approximatedirectorycontentindex_set.all().delete()
        package.approximatedirectorystructureindex_set.all().delete()
        package.exactfileindex_set.all().delete()
        package.resources.all().delete()

    scan_index_errors = []
    try:
        logger.info(f'Indexing Resources and fingerprints related to {package.package_url} from scan data')
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


def index_package(scannable_uri, package, scan_data, summary_data, reindex=False):
    scan_index_errors = []
    try:
        indexing_errors = index_package_files(package, scan_data, reindex=reindex)
        scan_index_errors.extend(indexing_errors)
        declared_license_expression = summary_data.get('declared_license_expression')
        declared_license_expression_spdx = None
        if declared_license_expression:
            declared_license_expression_spdx = build_spdx_license_expression(declared_license_expression)

        other_license_expressions = summary_data.get('other_license_expressions', [])
        other_license_expressions = [l['value'] for l in other_license_expressions if l['value']]
        other_license_expression = combine_expressions(other_license_expressions)

        copyright = ''
        declared_holder = summary_data.get('declared_holder')
        if declared_holder:
            copyright = f'Copyright (c) {declared_holder}'

        values_by_updateable_fields = {
            'summary': summary_data,
            'declared_license_expression': declared_license_expression,
            'declared_license_expression_spdx': declared_license_expression_spdx,
            'other_license_expression': other_license_expression,
            'copyright': copyright,
        }

        updated_fields = []
        for field, value in values_by_updateable_fields.items():
            p_val = getattr(package, field)
            if (
                (not p_val and value)
                or reindex
            ):
                setattr(package, field, value)
                entry = dict(
                    field=field,
                    old_value=p_val,
                    new_value=value,
                )
                updated_fields.append(entry)

        if updated_fields:
            data = {
                'updated_fields': updated_fields,
            }
            package.append_to_history(
                'Package field values have been updated.',
                data=data,
                save=True,
            )

        scannable_uri.scan_status = ScannableURI.SCAN_INDEXED
    except Exception as e:
        traceback_message = traceback.format_exc()
        error_message = traceback_message + '\n'
        # TODO: We should rerun the specific indexers that have failed
        if scan_index_errors:
            error_message += '\n'.join(scan_index_errors)
        scannable_uri.index_error = error_message
        scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
