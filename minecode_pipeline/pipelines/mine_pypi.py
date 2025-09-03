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

from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode

from minecode_pipeline.pipes import pypi


class MineandPublishPypiPURLs(Pipeline):
    """
    Mine all packageURLs from a pypi index and publish them to
    a FederatedCode repo.
    """

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.mine_pypi_packages,
            cls.mine_and_publish_pypi_packageurls,
        )

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available()

    def mine_pypi_packages(self):
        """Mine pypi package names from pypi indexes."""
        self.pypi_packages = pypi.mine_pypi_packages(logger=self.log)

    def mine_and_publish_pypi_packageurls(self):
        """Get pypi packageURLs for all mined pypi package names."""
        pypi.mine_and_publish_pypi_packageurls(packages=self.pypi_packages, logger=self.log)
