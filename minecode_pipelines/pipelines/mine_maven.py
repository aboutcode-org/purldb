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


from minecode_pipelines.pipes import maven
from scanpipe.pipelines.publish_to_federatedcode import PublishToFederatedCode


class MineMaven(PublishToFederatedCode):
    """
    Create DiscoveredPackages for packages found on maven:
    - input: url of maven repo
    - process index
      - collect purls, grouped by package
      - write to files
      - publish to fetchcode
      - loop

    """

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.collect_packages_from_maven,
        )

    def collect_packages_from_maven(self):
        maven.collect_packages_from_maven(self.project, self.log)
