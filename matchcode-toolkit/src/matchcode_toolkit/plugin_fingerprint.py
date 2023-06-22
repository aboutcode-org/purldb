#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import attr

from commoncode.cliutils import PluggableCommandLineOption
from commoncode.cliutils import POST_SCAN_GROUP
from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints
from plugincode.post_scan import post_scan_impl
from plugincode.post_scan import PostScanPlugin


@post_scan_impl
class Fingerprint(PostScanPlugin):
    resource_attributes = dict(
        directory_content_fingerprint=attr.ib(default=None, repr=False),
        directory_structure_fingerprint=attr.ib(default=None, repr=False),
    )
    sort_order = 6

    options = [
        PluggableCommandLineOption(
            (
                '--fingerprint',
            ),
            is_flag=True,
            default=False,
            help='Compute directory fingerprints that are used for matching',
            help_group=POST_SCAN_GROUP,
            sort_order=20,
        )
    ]

    def is_enabled(self, fingerprint, **kwargs):
        return fingerprint

    def process_codebase(self, codebase, **kwargs):
        codebase = compute_codebase_directory_fingerprints(codebase)
