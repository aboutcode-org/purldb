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

from packageurl import PackageURL
from pathlib import Path
from aboutcode import hashid
from minecode_pipelines.pipes import write_data_to_yaml_file


def store_conan_packages(pacakge_name, versions_data, fed_repo):
    """Collect Conan package versions into purls and write them to the repo."""

    base_purl = PackageURL(type="conan", name=pacakge_name)

    updated_purls = []
    versions = list(versions_data["versions"].keys())
    for version in versions:
        purl = PackageURL(type="conan", name=pacakge_name, version=version).to_string()
        updated_purls.append(purl)

    ppath = hashid.get_package_purls_yml_file_path(base_purl)
    purl_file_full_path = Path(fed_repo.working_dir) / ppath
    write_data_to_yaml_file(path=purl_file_full_path, data=updated_purls)
    return purl_file_full_path, base_purl
