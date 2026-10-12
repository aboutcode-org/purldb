#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import unittest
from unittest.mock import patch

from packageurl import PackageURL

from packagedb.purl_url_utils import derive_download_url
from packagedb.purl_url_utils import generate_synthetic_download_url


class TestDeriveDownloadURL(unittest.TestCase):
    def test_provided_url_takes_precedence(self):
        provided = "https://example.com/lodash-4.17.21.tgz"
        result = derive_download_url("pkg:npm/lodash@4.17.21", provided)
        self.assertEqual(result, provided)

    @patch("packagedb.purl_url_utils.purl2url.get_download_url")
    def test_infers_url_from_purl(self, mock_get_download):
        expected = "https://rubygems.org/downloads/bundler-2.3.23.gem"
        mock_get_download.return_value = expected

        result = derive_download_url("pkg:gem/bundler@2.3.23")

        mock_get_download.assert_called_once_with("pkg:gem/bundler@2.3.23")
        self.assertEqual(result, expected)

    @patch("packagedb.purl_url_utils.purl2url.get_download_url")
    def test_falls_back_to_synthetic_url(self, mock_get_download):
        mock_get_download.side_effect = Exception("cannot infer")

        result = derive_download_url("pkg:generic/some-package@1.0.0")

        self.assertTrue(result.startswith("purl://"))
        self.assertIn("generic/some-package@1.0.0", result)

    def test_invalid_purl_does_not_raise(self):
        # Last-resort fallback: returns a purl:-prefixed string
        result = derive_download_url("not-a-valid-purl")
        self.assertIsNotNone(result)
        self.assertIn("purl:", result)


class TestGenerateSyntheticDownloadURL(unittest.TestCase):
    def test_basic(self):
        purl = PackageURL.from_string("pkg:npm/express@4.17.1")
        self.assertEqual(generate_synthetic_download_url(purl), "purl://npm/express@4.17.1")

    def test_includes_namespace(self):
        purl = PackageURL.from_string("pkg:maven/org.apache.commons/commons-lang3@3.12.0")
        url = generate_synthetic_download_url(purl)
        self.assertTrue(url.startswith("purl://maven/org.apache.commons/"))
        self.assertIn("commons-lang3@3.12.0", url)

    def test_qualifiers_differentiate_packages(self):
        # Maven JARs with different classifiers must produce different URLs
        purl1 = PackageURL.from_string("pkg:maven/com.example/lib@1.0.0")
        purl2 = PackageURL.from_string("pkg:maven/com.example/lib@1.0.0?classifier=sources")
        self.assertNotEqual(
            generate_synthetic_download_url(purl1),
            generate_synthetic_download_url(purl2),
        )

    def test_no_version(self):
        purl = PackageURL.from_string("pkg:npm/express")
        url = generate_synthetic_download_url(purl)
        self.assertNotIn("@", url)

    def test_includes_subpath(self):
        purl = PackageURL.from_string("pkg:github/user/repo@v1.0#path/to/file")
        url = generate_synthetic_download_url(purl)
        self.assertIn("#path/to/file", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
