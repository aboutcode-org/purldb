from unittest.mock import patch
from django.test import TestCase
from minecode.collectors.maven import fetch_parent, map_maven_package
from packageurl import PackageURL

class TestIssue197MavenMalformedPom(TestCase):
    def test_fetch_parent_with_malformed_pom_does_not_crash(self):
        with patch(
            "minecode.collectors.maven.get_maven_pom",
            side_effect=Exception("VersionRangeParseError: Unbounded range: [9"),
        ):
            result = fetch_parent(pom_text="<project></project>")
            self.assertIsNone(result)
    def test_map_maven_package_with_malformed_pom_does_not_crash(self):
        with patch(
            "minecode.collectors.maven.get_pom_text",
            return_value="<project></project>",
        ):
            with patch(
                "minecode.collectors.maven._parse",
                side_effect=Exception("VersionRangeParseError: Unbounded range: [9"),
            ):
                purl = PackageURL.from_string(
                    "pkg:maven/commons-codec/commons-codec@1.16.0"
                )
                db_package, error = map_maven_package(
                    package_url=purl,
                    package_content="binary",
                    pipelines=[],
                )
                self.assertIsNone(db_package)
                self.assertIn("Failed to parse POM", error)
