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

from matchcode_toolkit.fingerprinting import compute_directory_fingerprints

from scanpipe.pipelines.scan_package import ScanPackage
from scanpipe.pipes.codebase import ProjectCodebase


class ScanAndFingerprintPackage(ScanPackage):
    """
    Scan a single package archive with ScanCode-toolkit, then calculate the
    directory fingerprints of the codebase.

    The output is a summary of the scan results in JSON format.
    """

    @classmethod
    def steps(cls):
        return (
            cls.get_package_archive_input,
            cls.collect_archive_information,
            cls.extract_archive_to_codebase_directory,
            cls.run_scancode,
            cls.load_inventory_from_toolkit_scan,
            cls.fingerprint_codebase,
            cls.make_summary_from_scan_results,
        )

    scancode_options = [
        "--copyright",
        "--email",
        "--info",
        "--license",
        "--license-text",
        "--package",
        "--url",
        "--classify",
        "--is-license-text",
        "--summary",
    ]

    def fingerprint_codebase(self):
        """
        Compute directory fingerprints for matching purposes
        """
        project_codebase = ProjectCodebase(self.project)
        compute_directory_fingerprints(project_codebase)