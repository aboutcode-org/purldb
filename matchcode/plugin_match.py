#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import defaultdict
import os

import attr
import requests

from commoncode.cliutils import PluggableCommandLineOption
from commoncode.cliutils import POST_SCAN_GROUP
from matchcode.fingerprinting import compute_directory_fingerprints
from matchcode.utils import path_suffixes
from plugincode.post_scan import post_scan_impl
from plugincode.post_scan import PostScanPlugin

MATCHCODE_DIRECTORY_CONTENT_MATCHING_ENDPOINT = os.environ.get('MATCHCODE_DIRECTORY_CONTENT_MATCHING_ENDPOINT')
MATCHCODE_DIRECTORY_STRUCTURE_MATCHING_ENDPOINT = os.environ.get('MATCHCODE_DIRECTORY_STRUCTURE_MATCHING_ENDPOINT')


class PackageInfo:
    def __init__(self, packagedb_url):
        self.packagedb_url = packagedb_url
        self.package_resources = self.get_resources_from_packagedb(packagedb_url)
        self.package_resource_by_paths = self.create_package_resource_by_paths()

    @classmethod
    def get_resources_from_packagedb(cls, packagedb_url):
        # Get package resources
        package_resources = []
        response = requests.get(packagedb_url)
        if response:
            package_data = response.json()
            resources_url = package_data.get('resources')
            count = 1
            while True:
                url = f'{resources_url}?page={count}'
                response = requests.get(url)
                if response:
                    package_resources.extend(response.json())
                    count += 1
                else:
                    break
        return package_resources

    def create_package_resource_by_paths(self):
        return {
            package_resource.get('path'): package_resource
            for package_resource in self.package_resources
        }


def check_resource_path(resource, package_resources_by_path):
    """
    Check to see if `resource` exists in the set of package Resources
    `package_resources_by_path`
    """
    for path_suffix in path_suffixes(resource.path):
        if not path_suffix in package_resources_by_path:
            continue
        package_resource = package_resources_by_path[path_suffix]
        # Check to see if we have the same Resource
        if ((resource.is_file == True
                and package_resource.get('is_file') == True
                and resource.sha1 == package_resource.get('sha1', ''))
                or (resource.is_file == False
                and package_resource.get('is_file') == False)):
            return True
    return False


def determine_best_package_match(directory, codebase, package_info_by_packagedb_url):
    """
    For all potential package matches in `package_info_by_purl`, return the
    package whose codebase structure matches ours the most.
    """
    # Calculate the percent of package files found in codebase
    packgedb_urls_by_match_ratio = {}
    matched_codebase_paths_by_packagedb_url = defaultdict(list)
    for matched_packagedb_url, package_info in package_info_by_packagedb_url.items():
        matched_codebase_paths = matched_codebase_paths_by_packagedb_url[matched_packagedb_url]
        package_resource_by_paths = package_info.package_resource_by_paths

        # TODO: Theres a problem when try to match the directory with
        # the name `package` because on the index side, we have the path
        # `package` indexed, but the path suffixes function only returns
        # paths that are at least two segments long
        #
        # We get around this by checking filetype (file or directory) in `check_resource_path`
        if check_resource_path(directory, package_resource_by_paths):
            matched_codebase_paths.append(directory.path)

        for child in directory.walk(codebase, topdown=True):
            if check_resource_path(child, package_resource_by_paths):
                matched_codebase_paths.append(child.path)

        matching_resources_count = len(matched_codebase_paths)
        ratio = matching_resources_count / len(package_resource_by_paths)
        packgedb_urls_by_match_ratio[ratio] = matched_packagedb_url

    highest_match_ratio = max(match_ratio for match_ratio, _ in packgedb_urls_by_match_ratio.items())
    best_package_match_packagedb_url = packgedb_urls_by_match_ratio[highest_match_ratio]
    return best_package_match_packagedb_url, matched_codebase_paths_by_packagedb_url[best_package_match_packagedb_url]


def do_directory_matching(codebase, fingerprint_key, matching_endpoint):
    for resource in codebase.walk(topdown=True):
        # Collect directory fingerprints, if available
        directory_fingerprint = resource.extra_data.get(fingerprint_key, '')

        # Skip resource if it is not a directory, does not contain directory
        # fingerprints, or if it has already been matched
        if (resource.is_file
                or not directory_fingerprint
                or resource.extra_data.get('matched', False)):
            continue

        # Send fingerprint to matchcode for matching and get the purls of
        # the matched packages
        payload = {
            'fingerprint': [directory_fingerprint]
        }
        response = requests.get(matching_endpoint, params=payload)
        if response:
            results = response.json()
            matched_packagedb_urls = [result.get('package', '') for result in results]
        if not matched_packagedb_urls:
            continue

        # Get the paths of the resources from matched packages
        package_info_by_packagedb_url = {}
        for packagedb_url in matched_packagedb_urls:
            package_info_by_packagedb_url[packagedb_url] = PackageInfo(packagedb_url)

        # Calculate the percent of package files found in codebase
        best_package_match_packagedb_url, matched_codebase_paths = determine_best_package_match(
            resource,
            codebase,
            package_info_by_packagedb_url
        )

        # Query PackageDB for info on the best matched package
        response = requests.get(best_package_match_packagedb_url)
        if response:
            # Create DiscoveredPackage for the best matched package
            package_data = response.json()
            if package_data not in codebase.attributes.matches:
                codebase.attributes.matches.append(package_data)
            best_package_match_purl = package_data['purl']

        # Associate the package to the resource and its children
        for matched_codebase_path in matched_codebase_paths:
            #print('matched_codebase_path: ' + matched_codebase_path)
            r = codebase.get_resource(matched_codebase_path)
            if best_package_match_purl in r.matched_to:
                continue
            r.matched_to.append(best_package_match_purl)
            r.extra_data['matched'] = True
            r.save(codebase)
    return codebase


@post_scan_impl
class Match(PostScanPlugin):
    codebase_attributes = dict(
        # a list of matches
        matches=attr.ib(default=attr.Factory(list), repr=False),
    )
    resource_attributes = dict(
        # a list of purls of the packages that a file is a part of
        matched_to=attr.ib(default=attr.Factory(list), repr=False),
    )

    sort_order = 6

    options = [
        PluggableCommandLineOption(
            (
                '-m',
                '--match',
            ),
            is_flag=True,
            default=False,
            help='Scan <input> for application package and dependency manifests, lockfiles and related data.',
            help_group=POST_SCAN_GROUP,
            sort_order=20,
        )
    ]

    def is_enabled(self, match, **kwargs):
        return match

    def process_codebase(self, codebase, **kwargs):
        codebase = compute_directory_fingerprints(codebase)
        codebase = do_directory_matching(
            codebase,
            'directory_content',
            MATCHCODE_DIRECTORY_CONTENT_MATCHING_ENDPOINT
        )
        codebase = do_directory_matching(
            codebase,
            'directory_structure',
            MATCHCODE_DIRECTORY_STRUCTURE_MATCHING_ENDPOINT
        )
