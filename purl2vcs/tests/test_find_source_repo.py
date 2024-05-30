#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import os
from unittest import mock
from unittest.mock import patch

from django.test import TestCase
from packageurl import PackageURL

from packagedb.models import Package, PackageContentType, Resource
from purl2vcs.find_source_repo import (
    convert_repo_urls_to_purls,
    fetch_response,
    get_repo_urls,
    get_source_repo,
    get_source_urls_from_package_data_and_resources,
    get_tag_and_commit,
    get_tags_and_commits,
    get_urls_from_package_data,
    get_urls_from_package_resources,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DATA = os.path.join(BASE_DIR, "testfiles", "find_source_repo", "tags_commits.txt")
TAGS_COMMITS_FILE = os.path.join(
    BASE_DIR, "testfiles", "find_source_repo", "tags_commits_list.txt"
)


class TestFindSourceRepo(TestCase):
    def setUp(self):
        self.package_with_resources_and_package_data = Package.objects.create(
            type="maven",
            namespace="com.nimbusds",
            name="oauth2-oidc-sdk",
            version="9.35",
            package_content=PackageContentType.SOURCE_ARCHIVE,
            download_url="https://repo1.maven.org/maven2/com/nimbusds/oauth2-oidc-sdk/9.35/oauth2-oidc-sdk-9.35.jar",
            vcs_url="git+https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions.git",
            homepage_url="https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            code_view_url="https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/src/master/",
        )
        Resource.objects.create(
            package=self.package_with_resources_and_package_data,
            path="oauth2-oidc-sdk-9.35-sources.jar",
            is_key_file=False,
            urls=[
                {
                    "url": "https://repo1.maven.org/maven2/com/nimbusds/oauth2-oidc-sdk/9.35/oauth2-oidc-sdk-9.35-sources.jar",
                }
            ],
        )
        Resource.objects.create(
            package=self.package_with_resources_and_package_data,
            path="Manifest.MF",
            is_key_file=True,
            urls=[
                {
                    "url": "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
                }
            ],
        )
        Resource.objects.create(
            package=self.package_with_resources_and_package_data,
            path="Manifest-1.MF",
            is_key_file=True,
            urls=[
                {
                    "url": "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/tree/master/oauth-oidc-sdk/src/main/resources/META-INF/MANIFEST.MF",
                }
            ],
        )
        self.package_without_resources_and_package_data = Package.objects.create(
            type="maven",
            namespace="com.nimbusds",
            name="oauth2-oidc-sdk",
            version="9.36",
            package_content=PackageContentType.SOURCE_ARCHIVE,
            download_url="https://repo1.maven.org/maven2/com/nimbusds/oauth2-oidc-sdk/9.36/oauth2-oidc-sdk-9.36.jar",
        )
        self.package_with_resources_and_without_package_data = Package.objects.create(
            type="maven",
            namespace="com.nimbusds",
            name="oauth2-oidc-sdk",
            version="9.37",
            package_content=PackageContentType.SOURCE_ARCHIVE,
            download_url="https://repo1.maven.org/maven2/com/nimbusds/oauth2-oidc-sdk/9.37/oauth2-oidc-sdk-9.37.jar",
        )
        Resource.objects.create(
            package=self.package_with_resources_and_without_package_data,
            path="oauth2-oidc-sdk-9.37-sources.jar",
            is_key_file=False,
            urls=[
                {
                    "url": "https://repo1.maven.org/maven2/com/nimbusds/oauth2-oidc-sdk/9.37/oauth2-oidc-sdk-9.37-sources.jar",
                }
            ],
        )
        Resource.objects.create(
            package=self.package_with_resources_and_without_package_data,
            path="Manifest.MF",
            is_key_file=True,
            urls=[
                {
                    "url": "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
                }
            ],
        )
        self.package_without_versions = Package.objects.create(
            type="maven",
            namespace="foo",
            name="bar",
            version="11",
            package_content=PackageContentType.SOURCE_ARCHIVE,
            download_url="https://repo1.maven.org/maven2/com/foo/bar/11/bar.11.jar",
        )

    @mock.patch("purl2vcs.find_source_repo.fetch_response")
    @mock.patch("purl2vcs.find_source_repo.get_urls_from_text")
    def test_get_source_purl_from_package_data(self, mock_text, mock_response):
        mock_response.side_effect = [
            None,
            None,
            None,
            None,
        ]
        mock_text.side_effect = [["https://bitbucket/ab/cd"], [], [], []]
        source_urls = list(
            get_urls_from_package_data(self.package_with_resources_and_package_data)
        )
        assert source_urls == [
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/src/master/",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "git+https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions.git",
            "https://bitbucket/ab/cd",
        ]

    def test_get_source_purl_from_package_resources(self):
        source_urls = list(
            get_urls_from_package_resources(
                self.package_with_resources_and_package_data
            )
        )
        assert source_urls == [
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/tree/master/oauth-oidc-sdk/src/main/resources/META-INF/MANIFEST.MF",
        ]

    @mock.patch("purl2vcs.find_source_repo.get_urls_from_package_data")
    @mock.patch(
        "purl2vcs.find_source_repo.get_merged_ancestor_package_from_maven_package"
    )
    def test_get_source_purl_from_package_data_and_resources(self, mock1, mock2):
        mock1.return_value = None
        mock2.return_value = []
        source_urls = get_source_urls_from_package_data_and_resources(
            self.package_without_resources_and_package_data
        )
        assert source_urls == []
        source_urls = get_source_urls_from_package_data_and_resources(
            self.package_with_resources_and_package_data
        )
        assert source_urls == [
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/tree/master/oauth-oidc-sdk/src/main/resources/META-INF/MANIFEST.MF",
        ]
        source_urls = get_source_urls_from_package_data_and_resources(
            self.package_with_resources_and_without_package_data
        )
        assert source_urls == [
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
        ]

    @mock.patch("purl2vcs.find_source_repo.get_urls_from_package_data")
    @mock.patch(
        "purl2vcs.find_source_repo.get_merged_ancestor_package_from_maven_package"
    )
    def test_get_repo_urls(self, mock1, mock2):
        mock1.return_value = None
        mock2.return_value = []
        source_urls = list(
            get_repo_urls(package=self.package_without_resources_and_package_data)
        )
        assert source_urls == [
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/tree/master/oauth-oidc-sdk/src/main/resources/META-INF/MANIFEST.MF",
        ]
        source_urls = list(get_repo_urls(package=self.package_without_versions))
        assert source_urls == []
        source_urls = list(
            get_repo_urls(package=self.package_with_resources_and_package_data)
        )
        assert source_urls == [
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/tree/master/oauth-oidc-sdk/src/main/resources/META-INF/MANIFEST.MF",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions",
            "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions/tree/master/oauth-oidc-sdk/src/main/resources/META-INF/MANIFEST.MF",
        ]

    def test_convert_repo_urls_to_purls(self):
        source_urls = list(
            convert_repo_urls_to_purls(
                [
                    "https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions"
                ]
            )
        )
        source_urls = [str(source_url) for source_url in source_urls]
        assert source_urls == [
            "pkg:bitbucket/connect2id/oauth-2.0-sdk-with-openid-connect-extensions"
        ]
        source_urls = list(
            convert_repo_urls_to_purls(
                [
                    "git+https://bitbucket.org/connect2id/oauth-2.0-sdk-with-openid-connect-extensions.git"
                ]
            )
        )
        source_urls = [str(source_url) for source_url in source_urls]
        assert source_urls == [
            "pkg:bitbucket/connect2id/oauth-2.0-sdk-with-openid-connect-extensions"
        ]

        assert list(
            convert_repo_urls_to_purls(
                ["git://github.com:maxmind/MaxMind-DB-Reader-java"]
            )
        ) == [
            PackageURL(
                type="github",
                namespace="maxmind",
                name="MaxMind-DB-Reader-java",
                version=None,
                qualifiers=None,
                subpath=None,
            )
        ]

        assert list(
            convert_repo_urls_to_purls(
                [
                    "git+https://github.com/ckeditor/ckeditor4-react.git@335af5b25923beaf5446652dcf2f06574f413779"
                ]
            )
        ) == [
            PackageURL(
                type="github",
                namespace="ckeditor",
                name="ckeditor4-react",
                version=None,
                qualifiers=None,
                subpath=None,
            )
        ]

        assert list(
            convert_repo_urls_to_purls(
                ["git+https://github.com/ckeditor/ckeditor4-react.git"]
            )
        ) == [
            PackageURL(
                type="github",
                namespace="ckeditor",
                name="ckeditor4-react",
                version=None,
                qualifiers=None,
                subpath=None,
            )
        ]

    def test_get_tags_commits(self):
        with patch("purl2vcs.find_source_repo.fetch_response"):
            with patch("subprocess.getoutput") as mock_popen:
                mock_popen.return_value = open(TEST_DATA).read()
                with open(TAGS_COMMITS_FILE) as f:
                    data = json.load(f)
                    tags_and_commits = []
                    for tag, commit in data:
                        tags_and_commits.append((tag, commit))
                    assert tags_and_commits == list(
                        get_tags_and_commits(
                            source_purl=PackageURL(
                                type="bitbucket",
                                namespace="connect2id",
                                name="oauth-2.0-sdk-with-openid-connect-extensions",
                            )
                        )
                    )
                    assert get_tag_and_commit(
                        version="9.35",
                        tags_and_commits=tags_and_commits,
                    ) == ("9.35", "fdc8117af75b192e3f8afcc0119c904b02686af8")

    def test_get_source_repo(self):
        with patch("purl2vcs.find_source_repo.fetch_response"):
            with patch("subprocess.getoutput") as mock_popen:
                mock_popen.return_value = open(TEST_DATA).read()
                assert get_source_repo(
                    package=self.package_without_resources_and_package_data,
                ) == PackageURL(
                    type="bitbucket",
                    namespace="connect2id",
                    name="oauth-2.0-sdk-with-openid-connect-extensions",
                    version="9.36",
                    qualifiers={"commit": "e86fb3431972d302fcb615aca0baed4d8ab89791"},
                    subpath=None,
                )

    @mock.patch("purl2vcs.find_source_repo.requests.get")
    def test_fetch_response(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "abc"
        assert fetch_response("https://github.com/assets") == None
        assert fetch_response("https://github.com/abc.js") == None

    def test_from_purl_to_git(self):
        response = self.client.get(
            "/api/from_purl/purl2git",
            data={"package_url": str(self.package_without_resources_and_package_data)},
            follow=True,
        )
        expected = "pkg:bitbucket/connect2id/oauth-2.0-sdk-with-openid-connect-extensions@9.36?commit=e86fb3431972d302fcb615aca0baed4d8ab89791"
        self.assertEqual(expected, response.data["git_repo"])
