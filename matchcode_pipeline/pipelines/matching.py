# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from scanpipe.pipelines.load_inventory import LoadInventory
from scanpipe.pipelines.scan_codebase import ScanCodebase
from matchcode_pipeline.pipes import matching
from scanpipe.pipes import matchcode


class Matching(ScanCodebase, LoadInventory):
    """
    1. Match archive to Packages
    2. Match archive to Resources
    3. Match directory exactly
    4. Match files exactly
    5. Match directories approximatly
    6. Match files approximately
    7. Matching on similar file attributes (path, type, extension, size, Java classpath, etc.)
    8. Return only the best matches (We could inject some user input, policies, we could provide a list of purls to guide matching, )

    new step:
    Focused matching based on list of existing packages in the codebase (or sbom input, codebase disclosure, or scan)
    validate package exists in purldb (raise warning)
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_inputs,
            cls.build_inventory_from_scans,
            cls.flag_empty_files,
            cls.match_archives_to_purldb_packages,
            cls.match_archives_to_purldb_resources,
            cls.fingerprint_codebase_directories,
            cls.match_directories_exact_to_purldb,
            cls.match_directories_to_purldb,
            cls.match_resources_to_purldb,
            cls.match_resources_approximately,
            cls.match_purldb_resources_post_process,
            cls.remove_packages_without_resources,
        )

    def fingerprint_codebase_directories(self):
        """Compute directory fingerprints for matching"""
        matchcode.fingerprint_codebase_directories(self.project)

    def match_archives_to_purldb_packages(self):
        """Match package archives against PurlDB packages"""
        matching.match_purldb_resources(
            project=self.project,
            matcher_func=matching.match_purldb_package,
            archives_only=True,
            logger=self.log,
        )

    def match_archives_to_purldb_resources(self):
        """Match package archives against PurlDB resources"""
        matching.match_purldb_resources(
            project=self.project,
            matcher_func=matching.match_purldb_resource,
            archives_only=True,
            logger=self.log,
        )

    def match_directories_to_purldb(self):
        """Match selected directories in PurlDB."""
        matching.match_purldb_directories(
            project=self.project,
            logger=self.log,
        )

    def match_directories_exact_to_purldb(self):
        """Match selected directories in PurlDB."""
        matching.match_purldb_directories(
            project=self.project,
            exact_directory_match=True,
            logger=self.log,
        )

    def match_resources_to_purldb(self):
        """Match selected files by extension in PurlDB."""
        matching.match_purldb_resources(
            project=self.project,
            matcher_func=matching.match_purldb_resource,
            logger=self.log,
        )

    def match_resources_approximately(self):
        """Match selected text files approximately in PurlDB"""
        matching.match_purldb_resources_approximately(
            project=self.project,
            logger=self.log,
        )

    def match_purldb_resources_post_process(self):
        """Choose the best package for PurlDB matched resources."""
        matching.match_purldb_resources_post_process(
            self.project, logger=self.log)

    def remove_packages_without_resources(self):
        """Remove packages without any resources."""
        package_without_resources = self.project.discoveredpackages.filter(
            codebase_resources__isnull=True
        )
        package_without_resources.delete()
