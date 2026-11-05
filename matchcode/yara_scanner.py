#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import os
from pathlib import Path
import re

from packageurl import PackageURL
import yara

logger = logging.getLogger(__name__)

DEFAULT_RULES_FILE = Path(__file__).resolve().parent / "rules" / "c_packages.yar"


class YaraPackageScanner:
    """Scan files or byte streams with compiled YARA rules to detect packages."""

    def __init__(self, rule_file_path=DEFAULT_RULES_FILE):
        self.rule_file_path = str(rule_file_path)
        self.rules = self.load_rules()

    def load_rules(self):
        """Compile and return YARA rules from the rule file."""
        if os.path.isfile(self.rule_file_path):
            return yara.compile(filepath=self.rule_file_path)

        logger.warning(f"YARA rule file not found: {self.rule_file_path}")
        return None

    def scan_data(self, byte_data):
        """Scan a raw byte buffer and return matching package details."""
        if not self.rules or not byte_data:
            return []

        return self._build_match_results(self.rules.match(data=byte_data))

    def _build_match_results(self, yara_matches):
        """Extract and normalize package data from raw YARA match objects."""
        package_results = []

        for yara_match in yara_matches:
            yara_rule_meta = yara_match.meta or {}
            purl_template = yara_rule_meta.get("purl_template")
            default_purl = yara_rule_meta.get("default_purl")
            version_pattern = yara_rule_meta.get("version_pattern")

            matched_strings = self._extract_matched_strings(yara_match)
            extracted_version = self._extract_version(version_pattern, matched_strings)

            package_url_str = None
            if extracted_version and purl_template:
                package_url_str = purl_template.format(version=extracted_version)
            elif default_purl:
                package_url_str = default_purl

            if not package_url_str:
                continue

            parsed_package_url = PackageURL.from_string(package_url_str)
            rule_string_ids = [
                yara_string.identifier for yara_string in getattr(yara_match, "strings", [])
            ]

            package_results.append(
                {
                    "rule": yara_match.rule,
                    "purl": str(parsed_package_url),
                    "package_data": {
                        "type": parsed_package_url.type,
                        "namespace": parsed_package_url.namespace,
                        "name": parsed_package_url.name,
                        "version": parsed_package_url.version,
                        "qualifiers": parsed_package_url.qualifiers or {},
                    },
                    "extracted_version": extracted_version,
                    "confidence": yara_rule_meta.get("confidence", "high"),
                    "description": yara_rule_meta.get("description", ""),
                    "category": yara_rule_meta.get("category", "c_library"),
                    "vendor": yara_rule_meta.get("vendor", ""),
                    "product": yara_rule_meta.get("product", ""),
                    "matched_strings": matched_strings or rule_string_ids,
                    "rule_strings": rule_string_ids,
                }
            )

        return package_results

    @staticmethod
    def _extract_matched_strings(yara_match):
        """Return unique decoded string literals matched by the YARA rule."""
        matched_strings = []
        seen = set()

        # In YARA, each rule string can match at multiple file offsets (instances)
        for yara_string in getattr(yara_match, "strings", []):
            for instance in getattr(yara_string, "instances", []):
                raw_bytes = getattr(instance, "matched_data", b"")
                # Safely decode arbitrary binary matches without failing on non-UTF-8 bytes
                text = raw_bytes.decode("utf-8", errors="replace").strip()
                if text and text not in seen:
                    seen.add(text)
                    matched_strings.append(text)

        return matched_strings

    @staticmethod
    def _extract_version(version_pattern, matched_strings):
        """Return the first regex version match found within matched strings."""
        if not version_pattern or not matched_strings:
            return None

        version_regex = re.compile(version_pattern)

        for text in matched_strings:
            match = version_regex.search(text)
            if match:
                # Extract the version subgroup if defined; fallback to the whole match
                return match.group(1) if match.groups() else match.group(0)

        return None
