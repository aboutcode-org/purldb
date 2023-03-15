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

from scanpipe.pipelines.scan_codebase import ScanCodebase
from scanpipe.pipes.codebase import ProjectCodebase

from matchcode_toolkit.fingerprinting import compute_directory_fingerprints


class ScanAndFingerprintCodebase(ScanCodebase):
    """
    A pipeline to scan a codebase with ScanCode-toolkit and compute directory
    fingerprints.

    Input files are copied to the project's codebase/ directory and are extracted
    in place before running the scan.
    Alternatively, the code can be manually copied to the project codebase/
    directory.
    """

    @classmethod
    def steps(cls):
        return (
            cls.copy_inputs_to_codebase_directory,
            cls.extract_archives,
            cls.collect_and_create_codebase_resources,
            cls.fingerprint_codebase,
            cls.tag_empty_files,
            cls.scan_for_application_packages,
            cls.scan_for_files,
        )

    # Set to True to extract recursively nested archives in archives.
    extract_recursively = False

    def fingerprint_codebase(self):
        """
        Compute directory fingerprints for matching purposes
        """
        project_codebase = ProjectCodebase(self.project)
        compute_directory_fingerprints(project_codebase)
