# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/nexB/scancode.io for support and download.

from collections import defaultdict
from os import getenv

from django.conf import settings
import requests

from packagedcode.models import build_package_uid
from matchcode_toolkit.fingerprinting import compute_directory_fingerprints
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import update_or_create_dependency
from scanpipe.pipes import update_or_create_package
from scanpipe.pipes.scancode import set_codebase_resource_for_package
from scanpipe.pipes.codebase import ProjectCodebase


def get_settings(var_name):
    """
    Return the settings value from the environment or Django settings.
    """
    return getenv(var_name) or getattr(settings, var_name, None) or ''


PURLDB_URL = get_settings('PURLDB_URL').rstrip('/')
MATCHCODE_ENDPOINT = f'{PURLDB_URL}/approximate_directory_content_index/match/' if PURLDB_URL else None
PURLDB_PACKAGE_ENDPOINT = f'{PURLDB_URL}/packages/' if PURLDB_URL else None
PURLDB_RESOURCE_ENDPOINT = f'{PURLDB_URL}/resources/' if PURLDB_URL else None

PURLDB_API_KEY = get_settings('PURLDB_API_KEY')
PURLDB_AUTH_HEADERS = {
    'Authorization': f'Token {PURLDB_API_KEY}'
} if PURLDB_API_KEY else {}


class PackageInfo:
    def __init__(self, package_link):
        self.package_link = package_link
        self.package_resources = self.get_resources_from_packagedb(package_link)
        self.package_resource_by_paths = self.create_package_resource_by_paths()

    @classmethod
    def get_resources_from_packagedb(cls, package_link):
        package_resources = []
        response = requests.get(package_link)
        if response.ok:
            resources_link = response.json().get('resources').rstrip('/')
            page_count = 1
            while True:
                resources_link_template = f'{resources_link}/?page={page_count}'
                response = requests.get(resources_link_template)
                if not response.ok:
                    break
                resources = response.json()
                package_resources.extend(resources)
                page_count += 1
        return package_resources

    def create_package_resource_by_paths(self):
        return {
            package_resource.get('path'): package_resource
            for package_resource in self.package_resources
        }


def path_suffixes(path):
    """
    Yield all the suffixes of `path`, starting from the longest (e.g. more segments).
    """
    segments = path.strip('/').split('/')
    suffixes = (segments[i:] for i in range(len(segments)))
    for suffix in suffixes:
        yield '/'.join(suffix)


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


def determine_best_package_match(directory, package_info_by_package_links):
    """
    For all potential package matches in `package_info_by_purl`, return the
    package whose codebase structure matches ours the most.
    """
    # Calculate the percent of package files found in codebase
    package_links_by_match_ratio = {}
    matched_codebase_paths_by_package_link = defaultdict(list)
    for package_link, package_info in package_info_by_package_links.items():
        matched_codebase_paths = matched_codebase_paths_by_package_link[package_link]
        package_resource_by_paths = package_info.package_resource_by_paths

        # TODO: Theres a problem when try to match the directory with
        # the name `package` because on the index side, we have the path
        # `package` indexed, but the path suffixes function only returns
        # paths that are at least two segments long
        #
        # We get around this by checking filetype (file or directory) in `check_resource_path`
        if check_resource_path(directory, package_resource_by_paths):
            matched_codebase_paths.append(directory.path)

        for child in directory.walk(topdown=True):
            if check_resource_path(child, package_resource_by_paths):
                matched_codebase_paths.append(child.path)

        matching_resources_count = len(matched_codebase_paths)
        ratio = matching_resources_count / len(package_resource_by_paths)
        package_links_by_match_ratio[ratio] = package_link

    highest_match_ratio = max(match_ratio for match_ratio, _ in package_links_by_match_ratio.items())
    best_package_match_link = package_links_by_match_ratio[highest_match_ratio]
    return best_package_match_link, matched_codebase_paths_by_package_link[best_package_match_link]


class Matching(Pipeline):
    @classmethod
    def steps(cls):
        return (
            cls.get_project_codebase,
            cls.create_fingerprints,
            cls.perform_matching,
        )

    def get_project_codebase(self):
        self.project_codebase = ProjectCodebase(self.project)

    def create_fingerprints(self):
        compute_directory_fingerprints(self.project_codebase)

    def perform_matching(self):
        for resource in self.project_codebase.walk(topdown=True):
            # Collect directory fingerprints, if available
            directory_content_fingerprint = resource.extra_data.get('directory_content', '')

            # Skip resource if it is not a directory, does not contain directory
            # fingerprints, or if it has already been matched
            if (resource.is_file
                    or not directory_content_fingerprint
                    or resource.extra_data.get('matched', False)):
                continue

            # Send fingerprint to matchcode for matching and get the purls of
            # the matched packages
            payload = {
                'fingerprint': [directory_content_fingerprint]
            }
            response = requests.get(MATCHCODE_ENDPOINT, params=payload)
            if response:
                results = response.json()
                matched_package_links = [result.get('package', '') for result in results]
            if not matched_package_links:
                continue

            # Get the paths of the resources from matched packages
            package_info_by_package_links = {}
            for link in matched_package_links:
                package_info_by_package_links[link] = PackageInfo(link)

            # Calculate the percent of package files found in codebase
            best_package_match_link, matched_codebase_paths = determine_best_package_match(resource, package_info_by_package_links)

            # Query PackageDB for info on the best matched package
            response = requests.get(best_package_match_link)
            if response:
                # Create DiscoveredPackage for the best matched package
                package_data = response.json()
                purl = package_data.get('purl', '')
                uuid = package_data.get('uuid', '')
                package_data['package_uid'] = f'{purl}?uuid={uuid}'
                package_data.pop('uuid')
                discovered_package = update_or_create_package(self.project, package_data)

            # Associate the package to the resource and its children
            for matched_codebase_path in matched_codebase_paths:
                r = self.project.codebaseresources.get(path=matched_codebase_path)
                set_codebase_resource_for_package(r, discovered_package)
                r.extra_data['matched'] = True
                r.save()

        # Try sha1 matching against PackageDB
        unmatched = self.project.codebaseresources.exclude(extra_data__contains={'matched': True}).exclude(sha1__isnull=True)
        for resource in unmatched:
            sha1_lookup_url = f'{PURLDB_PACKAGE_ENDPOINT}/?sha1={resource.sha1}'
            response = requests.get(sha1_lookup_url)
            if response:
                results = response.json().get('results', [])
                for result in results:
                    purl = result.get('purl', '')
                    uuid = result.pop('uuid')
                    package_uid = f'{purl}?uuid={uuid}'
                    result['package_uid'] = package_uid
                    dependencies = result.pop('dependencies')
                    discovered_package = update_or_create_package(self.project, result, resource)
                    if dependencies:
                        for dependency in dependencies:
                            purl = dependency.get('purl', '')
                            dep = {
                                'purl': purl,
                                'extracted_requirement': dependency.get('requirement', ''),
                                'scope': dependency.get('scope', ''),
                                'dependency_uid': build_package_uid(purl),
                                'is_runtime': dependency.get('is_runtime', False),
                                'is_optional': dependency.get('is_optional', False),
                                'is_resolved': dependency.get('is_resolved', False),
                                'for_package_uid': package_uid,
                            }
                            discovered_dependency = update_or_create_dependency(self.project, dep)
