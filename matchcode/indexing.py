#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import os
import sys

from commoncode.resource import VirtualCodebase

from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints
from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ExactPackageArchiveIndex
from matchcode.models import ExactFileIndex


TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def index_package_archives(package):
    """
    Index Package archives for matching

    Return True if an ExactPackageArchiveIndex has been created,
    otherwise return False
    """
    _, created = ExactPackageArchiveIndex.index(
        sha1=package.sha1,
        package=package,
    )
    return created


def index_package_file(resource):
    """
    Index Package files for matching

    Return a boolean, `created_exact_file_index`, which returns True if it has
    been created, False otherwise.
    """
    _, created_exact_file_index = ExactFileIndex.index(
        sha1=resource.sha1,
        package=resource.package
    )
    return created_exact_file_index


def _create_virtual_codebase_from_package_resources(package):
    """
    Return a VirtualCodebase from the resources of `package`
    """
    # Create something that looks like a scancode scan so we can import it into a VirtualCodebase
    # TODO: Evolve this into something more elaborate, e.g.
    #       Codebase class methods can manipulate Resource table entries
    package_resources = package.resources.order_by('path')
    if not package_resources:
        return

    files = []
    for resource in package_resources:
        files.append(
            {
                'path': resource.path,
                'size': resource.size,
                'sha1': resource.sha1,
                'md5': resource.md5,
                'type': resource.type,
            }
        )

    make_new_root = False
    sample_file_path = files[0].get('path', '')
    root_dir = sample_file_path.split('/')[0]
    for f in files:
        file_path = f.get('path', '')
        if not file_path.startswith(root_dir):
            make_new_root = True
            break

    if make_new_root:
        new_root = '{}-{}'.format(package.name, package.version)
        for f in files:
            new_path = os.path.join(new_root, f.get('path', ''))
            f['path'] = new_path

    # Create VirtualCodebase
    mock_scan = dict(files=files)
    return VirtualCodebase(location=mock_scan)


def index_directory_fingerprints(codebase, package):
    """
    Compute fingerprints for a directory from `codebase` and index them to
    ApproximateDirectoryContentIndex and ApproximateDirectoryStructureIndex

    Return a tuple of integers, `indexed_adci` and `indexed_adsi`, that
    represent the number of indexed ApproximateDirectoryContentIndex and
    ApproximateDirectoryStructureIndex created, respectivly.
    """
    indexed_adci = 0
    indexed_adsi = 0
    for resource in codebase.walk(topdown=False):
        directory_content_fingerprint = resource.extra_data.get('directory_content', '')
        directory_structure_fingerprint = resource.extra_data.get('directory_structure', '')

        if directory_content_fingerprint:
            _, adci_created = ApproximateDirectoryContentIndex.index(
                directory_fingerprint=directory_content_fingerprint,
                resource_path=resource.path,
                package=package,
            )
            if adci_created:
                indexed_adci += 1

        if directory_structure_fingerprint:
            _, adsi_created = ApproximateDirectoryStructureIndex.index(
                directory_fingerprint=directory_structure_fingerprint,
                resource_path=resource.path,
                package=package,
            )
            if adsi_created:
                indexed_adsi += 1

    return indexed_adci, indexed_adsi


def index_package_directories(package):
    """
    Index the directories of `package` to ApproximateDirectoryContentIndex and
    ApproximateDirectoryStructureIndex

    Return a tuple of integers, `indexed_adci` and `indexed_adsi`, that
    represent the number of indexed ApproximateDirectoryContentIndex and
    ApproximateDirectoryStructureIndex created, respectivly.

    Return 0, 0 if a VirtualCodebase cannot be created from the Resources of a
    Package
    """
    vc = _create_virtual_codebase_from_package_resources(package)
    if not vc:
        return 0, 0

    vc = compute_codebase_directory_fingerprints(vc)
    return index_directory_fingerprints(vc, package)
