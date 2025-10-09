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

import base64
from shutil import rmtree

from aboutcode import hashid
from packagedcode.models import PackageData
from packagedcode.models import Party
from packageurl import PackageURL
from scanpipe.pipes import federatedcode
from scanpipe.pipes.fetch import fetch_http
from scanpipe.pipes.scancode import extract_archives

from minecode_pipelines import pipes
from minecode_pipelines import VERSION

ALPINE_CHECKPOINT_PATH = "alpine/checkpoints.json"

# We are testing and storing mined packageURLs in one single repo per ecosystem for now
MINECODE_DATA_ALPINE_REPO = "https://github.com/aboutcode-data/minecode-data-alpine-test"

# Number of packages
PACKAGE_BATCH_SIZE = 1000
ALPINE_LINUX_APKINDEX_URLS = [
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/edge/testing/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.0/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.0/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.0/testing/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.0/testing/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.1/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.1/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.1/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.1/testing/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.10/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.11/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/mips64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/mips64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.12/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/mips64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/mips64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.13/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/mips64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/mips64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.14/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.15/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.16/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.17/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.18/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.2/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.2/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.2/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/loongarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/riscv64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.3/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.3/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.3/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.3/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.3/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.3/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.4/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.4/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.4/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.4/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.4/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.4/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.5/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.6/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.7/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.8/main/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/community/x86_64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/aarch64/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/armhf/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/armv7/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/ppc64le/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/s390x/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/x86/APKINDEX.tar.gz",
    "https://dl-cdn.alpinelinux.org/alpine/v3.9/main/x86_64/APKINDEX.tar.gz",
]


def parse_email(text):
    """
    Return a tuple of (name, email) extracted from a `text` string.
        Debian TeX Maintainers <debian-tex-maint@lists.debian.org>
    """
    if not text:
        return None, None
    name, _, email = text.partition("<")
    email = email.strip(">")
    name = name.strip()
    email = email.strip()
    return name or None, email or None


def build_package(extracted_pkginfo, distro, repo):
    name = extracted_pkginfo.get("name")
    version = extracted_pkginfo.get("version")
    arch = extracted_pkginfo.get("arch")
    qualifiers = {
        "arch": arch,
        "distro": distro,
    }
    description = extracted_pkginfo.get("description")
    extracted_license_statement = extracted_pkginfo.get("license")
    repository_homepage_url = extracted_pkginfo.get("url")
    size = extracted_pkginfo.get("size")
    apk_checksum = extracted_pkginfo.get("checksum")
    sha1 = apk_checksum_to_sha1(apk_checksum)
    apk_download_url = (
        f"https://dl-cdn.alpinelinux.org/alpine/{distro}/{repo}/{arch}/{name}-{version}.apk"
    )

    parties = []
    maintainer = extracted_pkginfo.get("maintainer")
    if maintainer:
        maintainer_name, maintainer_email = parse_email(maintainer)
        if maintainer_name:
            party = Party(name=maintainer_name, role="maintainer", email=maintainer_email)
            parties.append(party)

    purl = PackageURL(
        type="apk", namespace="alpine", name=name, version=version, qualifiers=qualifiers
    )
    download_data = dict(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        version=purl.version,
        qualifiers=purl.qualifiers,
        description=description,
        repository_homepage_url=repository_homepage_url,
        extracted_license_statement=extracted_license_statement,
        parties=parties,
        size=size,
        sha1=sha1,
        download_url=apk_download_url,
        datasource_id="alpine_metadata",
    )
    package = PackageData.from_data(download_data)

    return package


def parse_apkindex(data: str):
    """
    Parse an APKINDEX format string into a list of package dictionaries.
    https://wiki.alpinelinux.org/wiki/Apk_spec
    """
    current_pkg = {}

    for line in data.splitlines():
        line = line.strip()
        if not line:
            if current_pkg:
                yield current_pkg
                current_pkg = {}
            continue

        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()

        mapping = {
            "C": "checksum",
            "P": "name",
            "V": "version",
            "A": "arch",
            "S": "size",
            "I": "installed_size",
            "T": "description",
            "U": "url",
            "L": "license",
            "o": "origin",
            "m": "maintainer",
            "t": "build_time",
            "c": "commit",
            "k": "provider_priority",
            "D": "depends",
            "p": "provides",
            "i": "install_if",
        }

        field = mapping.get(key, key)

        if key in ("D", "p", "i"):
            current_pkg[field] = value.split()
        elif key in ("S", "I", "t", "k"):
            try:
                current_pkg[field] = int(value)
            except ValueError:
                current_pkg[field] = value
        else:
            current_pkg[field] = value

    if current_pkg:
        yield current_pkg


def apk_checksum_to_sha1(apk_checksum: str) -> str:
    """
    Convert an Alpine APKINDEX package checksum (Q1... format)
    into its SHA-1 hex digest.
    """
    if not apk_checksum.startswith("Q1"):
        raise ValueError("Invalid checksum format: must start with 'Q1'")

    # Drop the "Q1" prefix
    b64_part = apk_checksum[2:]

    # Decode from base64
    sha1_bytes = base64.b64decode(b64_part)

    # Convert to hex
    return sha1_bytes.hex()


class AlpineCollector:
    """
    Download and process an Alpine APKINDEX.tar.gz file for Packages
    """

    def __init__(self):
        self.index_downloads = []

    def __del__(self):
        if self.index_downloads:
            for download in self.index_downloads:
                rmtree(download.directory)

    def _fetch_index(self, uri):
        """
        Return a temporary location where the alpine index was saved.
        """
        index = fetch_http(uri)
        self.index_downloads.append(index)
        return index

    def get_packages(self, logger=None):
        """Yield Package objects from alpine index"""
        for apkindex_url in ALPINE_LINUX_APKINDEX_URLS:
            _, subpath = apkindex_url.split("https://dl-cdn.alpinelinux.org/alpine/")
            distro, repo, _, _ = subpath.split("/")
            index = self._fetch_index(uri=apkindex_url)
            extract_archives(location=index.path)
            index_location = f"{index.path}-extract/APKINDEX"
            with open(index_location, encoding="utf-8") as f:
                for pkg in parse_apkindex(f.read()):
                    pd = build_package(pkg, distro=distro, repo=repo)
                    current_purl = PackageURL(
                        type=pd.type,
                        namespace=pd.namespace,
                        name=pd.name,
                    )
                    yield current_purl, pd


def commit_message(commit_batch, total_commit_batch="many"):
    from django.conf import settings

    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    tool_name = "pkg:github/aboutcode-org/scancode.io"

    return f"""\
        Collect PackageURLs from Alpine ({commit_batch}/{total_commit_batch})

        Tool: {tool_name}@v{VERSION}
        Reference: https://{settings.ALLOWED_HOSTS[0]}

        Signed-off-by: {author_name} <{author_email}>
        """


def collect_packages_from_alpine(files_per_commit=PACKAGE_BATCH_SIZE, logger=None):
    # Clone data and config repo
    data_repo = federatedcode.clone_repository(
        repo_url=MINECODE_DATA_ALPINE_REPO,
        logger=logger,
    )
    config_repo = federatedcode.clone_repository(
        repo_url=pipes.MINECODE_PIPELINES_CONFIG_REPO,
        logger=logger,
    )
    if logger:
        logger(f"{MINECODE_DATA_ALPINE_REPO} repo cloned at: {data_repo.working_dir}")
        logger(f"{pipes.MINECODE_PIPELINES_CONFIG_REPO} repo cloned at: {config_repo.working_dir}")

    # download and iterate through alpine indices
    alpine_collector = AlpineCollector()
    files_to_commit = []
    commit_batch = 1
    for current_purl, package in alpine_collector.get_packages():
        # write packageURL to file
        package_base_dir = hashid.get_package_base_dir(purl=current_purl)
        purl_file = pipes.write_packageurls_to_file(
            repo=data_repo,
            base_dir=package_base_dir,
            packageurls=[package.purl],
            append=True,
        )
        if purl_file not in files_to_commit:
            files_to_commit.append(purl_file)

        if len(files_to_commit) == files_per_commit:
            federatedcode.commit_and_push_changes(
                commit_message=commit_message(commit_batch),
                repo=data_repo,
                files_to_commit=files_to_commit,
                logger=logger,
            )
            files_to_commit.clear()
            commit_batch += 1

    if files_to_commit:
        federatedcode.commit_and_push_changes(
            commit_message=commit_message(commit_batch),
            repo=data_repo,
            files_to_commit=files_to_commit,
            logger=logger,
        )

    repos_to_clean = [data_repo, config_repo]
    return repos_to_clean
