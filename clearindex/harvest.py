#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import sys

from django.db import transaction
from django.utils import timezone

from packagedb.models import Package
from packagedb.models import Resource

from minecode.management.commands.run_map import merge_packages
from minecode.utils import stringify_null_purl_fields


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def get_resource_license_expressions(file_data):
    """
    Return a string that contains all the license_expression statements (deduped),
    with a newline separating each or None if there are no license_expression statements
    in the scan data.
    """
    license_expressions = file_data.get('license_expressions', []) or []
    if license_expressions == []:
        return

    expressions = set(list(expression for expression in license_expressions))

    return '\n'.join(expressions)


def get_resource_copyright_statements(file_data):
    """
    Return a string that contains all the copyright statements (deduped), with a newline
    separating each or None if there are no copyright statements in the scan data.
    """
    copyrights = file_data.get('copyrights', []) or []
    if copyrights == []:
        return

    statements = set(list(copyright.get('value') for copyright in copyrights))

    return '\n'.join(statements)


def create_from_harvest(package_scan={}, files_data=[], cditem_path=''):
    """
    Return a Package object, created or updated via a ScanCode-Toolkit "package" scan.
    """
    fields = (
        'type',
        'namespace',
        'name',
        'version',
        'qualifiers',
        'subpath',
        'primary_language',
        'description',
        'keywords',
        'homepage_url',
        'download_url',
        'size',
        'sha1',
        'md5',
        'sha256',
        'sha512',
        'bug_tracking_url',
        'code_view_url',
        'vcs_url',
        'copyright',
        'license_expression',
        'declared_license',
        'notice_text',
        'source_packages',
    )

    package_data = {field_name: package_scan.get(field_name) for field_name in fields}

    stringify_null_purl_fields(package_data)

    pkg_type = package_data.get('type')
    namespace = package_data.get('namespace')
    name = package_data.get('name')
    version = package_data.get('version')
    qualifiers = package_data.get('qualifiers')
    subpath = package_data.get('subpath')

    download_url = package_data.get('download_url')
    if not download_url:
        logger.error('Null `download_url` value for `package_data`: {}'.format(package_data))
        return

    # This ugly block is needed until https://github.com/nexB/packagedb/issues/14
    # is complete.
    try:
        package = Package.objects.get(
            type=pkg_type,
            namespace=namespace,
            name=name,
            version=version,
            qualifiers=qualifiers,
            subpath=subpath,
            download_url=download_url
        )
        # Merge package records if it already exists
        merge_packages(
            existing_package=package,
            new_package_data=package_data,
            replace=False
        )
        package.append_to_history('Updated package from CDitem harvest: {}'.format(cditem_path))

        logger.info('Merged package data from scancode harvest: {}'.format(package))

    except Package.DoesNotExist:
        try:
            package = Package.objects.get(download_url=download_url)
            # Merge package records if it already exists
            merge_packages(
                existing_package=package,
                new_package_data=package_data,
                replace=False
            )
            package.append_to_history('Updated package from CDitem harvest: {}'.format(cditem_path))

            logger.info('Merged package data from scancode harvest: {}'.format(package))

        except Package.DoesNotExist:
            package = Package.objects.create(**package_data)
            package.append_to_history('Created package from CDitem harvest: {}'.format(cditem_path))

            logger.info('Created package from scancode harvest: {}'.format(package))

    # Now, add resources to the Package.
    for f in files_data:
        path = f.get('path')
        is_file = f.get('type', '') == 'file'
        copyright = get_resource_copyright_statements(f)
        license_expression = get_resource_license_expressions(f)
        file_data = dict(
            package=package,
            path=path,
            size=f.get('size'),
            sha1=f.get('sha1'),
            md5=f.get('md5'),
            sha256=f.get('sha256'),
            git_sha1=f.get('git_sha1'),
            is_file=is_file,
            copyright=copyright,
            license_expression=license_expression,
        )

        # Ensure there will be no `path` collision
        try:
            Resource.objects.get(package=package, path=path)
        except Resource.DoesNotExist:
            Resource.objects.create(**file_data)

    return package


def map_scancode_harvest(cditem):
    """
    Return the number of created or merged Packages from a scancode harvest and create
    its Resources.
    """
    with transaction.atomic():
        try:
            harvest_data = cditem.data
        except ValueError:
            err_msg = 'CDitemError: empty content field for CDitem: {}'.format(cditem.path)
            logger.error(err_msg)

            cditem.map_error = err_msg
            cditem.save()
            return 0

        content = harvest_data.get('content', {}) or {}
        files_data = content.get('files', []) or []
        summary = content.get('summary', {}) or {}
        packages = summary.get('packages', []) or []

        for package_scan in packages:
            # Check if there is a valid download url. Missing download_url values are
            # considered map_errors, as a Package object cannot have a `Null`
            # download_url value.
            download_url = package_scan.get('download_url')
            if not download_url:
                purl = package_scan.get('purl')
                err_msg = 'CDitemError: empty download_url for package: {}'.format(purl)
                logger.error(err_msg)

                cditem.map_error = err_msg
                cditem.save()
                continue

            # Package + Resource creation
            # pass the `path` of the CDitem for logging purposes
            create_from_harvest(package_scan, files_data, cditem.path)

        cditem.last_map_date = timezone.now()
        cditem.save()

        return len(packages)
