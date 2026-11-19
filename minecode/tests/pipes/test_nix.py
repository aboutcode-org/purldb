#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest import mock

from minecode.pipes import INITIAL_SYNC_STATE
from minecode.pipes import PERIODIC_SYNC_STATE
from minecode.pipes import nix


class TestMinecodeNixPipe(TestCase):
    def test_get_nix_base_purl(self):
        self.assertEqual("pkg:nix/nixpkgs/git", nix.get_nix_base_purl("git"))
        self.assertEqual("pkg:nix/nixpkgs/python3", nix.get_nix_base_purl("python3"))

    def test_get_nix_packages_to_sync_skips_already_mined_packages_initial_sync(self):
        names = ["git", "python3", "ripgrep", "curl"]
        with tempfile.TemporaryDirectory() as tmpdir:
            packages_file = Path(tmpdir) / "packages.json"
            packages_file.write_text(json.dumps({"packages": names}))

            with mock.patch.object(
                nix,
                "get_mined_packages_from_checkpoint",
                return_value=["pkg:nix/nixpkgs/git", "pkg:nix/nixpkgs/curl"],
            ):
                packages_to_sync, synced = nix.get_nix_packages_to_sync(
                    packages_file=str(packages_file),
                    state=INITIAL_SYNC_STATE,
                )

        self.assertEqual(["python3", "ripgrep"], sorted(packages_to_sync))
        self.assertEqual(["pkg:nix/nixpkgs/git", "pkg:nix/nixpkgs/curl"], synced)

    def test_get_nix_packages_to_sync_skips_already_mined_packages_periodic_sync(self):
        names = ["git", "python3", "ripgrep"]
        with tempfile.TemporaryDirectory() as tmpdir:
            packages_file = Path(tmpdir) / "packages.json"
            packages_file.write_text(json.dumps({"packages": names}))

            with mock.patch.object(
                nix,
                "get_mined_packages_from_checkpoint",
                return_value=["pkg:nix/nixpkgs/git"],
            ):
                packages_to_sync, synced = nix.get_nix_packages_to_sync(
                    packages_file=str(packages_file),
                    state=PERIODIC_SYNC_STATE,
                )

        self.assertEqual(["python3", "ripgrep"], sorted(packages_to_sync))
        self.assertEqual(["pkg:nix/nixpkgs/git"], synced)

    def test_get_nix_packages_to_sync_handles_legacy_raw_names_checkpoint(self):
        names = ["git", "python3", "ripgrep"]
        with tempfile.TemporaryDirectory() as tmpdir:
            packages_file = Path(tmpdir) / "packages.json"
            packages_file.write_text(json.dumps({"packages": names}))

            with mock.patch.object(
                nix,
                "get_mined_packages_from_checkpoint",
                return_value=["git"],
            ):
                packages_to_sync, synced = nix.get_nix_packages_to_sync(
                    packages_file=str(packages_file),
                    state=INITIAL_SYNC_STATE,
                )

        self.assertEqual(["python3", "ripgrep"], sorted(packages_to_sync))
        self.assertEqual(["git"], synced)
