#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.apps import apps

from minecode.utils_test import TestMigrations


class TestPopulateHasErrorFields(TestMigrations):
    app_name = "minecode"
    migrate_from = "0024_remove_resourceuri_minecode_re_is_visi_51562c_idx_and_more"
    migrate_to = "0025_populate_has_error_fields"

    def setUpBeforeMigration(self, apps):
        # using get_model to avoid circular import
        ResourceURI = apps.get_model("minecode", "ResourceURI")

        self.resource_uris = [
            ResourceURI.objects.create(
                uri="http://example.com/1",
                map_error="error",
                visit_error="error",
            ),
            ResourceURI.objects.create(
                uri="http://example.com/2",
                visit_error="error",
            ),
            ResourceURI.objects.create(
                uri="http://example.com/3",
                map_error="error",
            ),
            ResourceURI.objects.create(
                uri="http://example.com/4",
            ),
        ]

        for resource_uri in self.resource_uris:
            resource_uri.save()

    def test_populate_has_error_fields(self):
        # using get_model to avoid circular import
        ResourceURI = apps.get_model("minecode", "ResourceURI")
        results = list(
            ResourceURI.objects.values(
                "uri",
                "has_map_error",
                "map_error",
                "has_visit_error",
                "visit_error",
            ).order_by("uri")
        )
        expected = [
            {
                "has_map_error": True,
                "has_visit_error": True,
                "map_error": "error",
                "uri": "http://example.com/1",
                "visit_error": "error",
            },
            {
                "has_map_error": False,
                "has_visit_error": True,
                "map_error": None,
                "uri": "http://example.com/2",
                "visit_error": "error",
            },
            {
                "has_map_error": True,
                "has_visit_error": False,
                "map_error": "error",
                "uri": "http://example.com/3",
                "visit_error": None,
            },
            {
                "has_map_error": False,
                "has_visit_error": False,
                "map_error": None,
                "uri": "http://example.com/4",
                "visit_error": None,
            },
        ]
        self.assertEqual(results, expected)


class TestSetIsVisitableForMavenIndexURIs(TestMigrations):
    app_name = "minecode"
    migrate_from = "0025_populate_has_error_fields"
    migrate_to = "0026_set_is_visitable_for_maven_index_uris"

    def setUpBeforeMigration(self, apps):
        # using get_model to avoid circular import
        ResourceURI = apps.get_model("minecode", "ResourceURI")

        self.resource_uris = [
            ResourceURI.objects.create(
                uri="maven-index://repo1.maven.org/zone/src/sheaf/logback-sheaf/1.1.7/logback-sheaf-1.1.7.jar",
                is_visitable=True,
            ),
            ResourceURI.objects.create(
                uri="maven-index://repo1.maven.org/zone/src/sheaf/logback-sheaf/1.1.7/logback-sheaf-1.1.8.jar",
                is_visitable=False,
            ),
        ]

        for resource_uri in self.resource_uris:
            resource_uri.save()

    def test_set_is_visitable_for_maven_index_uris(self):
        # using get_model to avoid circular import
        ResourceURI = apps.get_model("minecode", "ResourceURI")
        results = list(
            ResourceURI.objects.values(
                "uri",
                "is_visitable",
            ).all()
        )
        expected = [
            {
                "is_visitable": False,
                "uri": "maven-index://repo1.maven.org/zone/src/sheaf/logback-sheaf/1.1.7/logback-sheaf-1.1.8.jar",
            },
            {
                "is_visitable": False,
                "uri": "maven-index://repo1.maven.org/zone/src/sheaf/logback-sheaf/1.1.7/logback-sheaf-1.1.7.jar",
            },
        ]
        self.assertEqual(results, expected)


class TestReplaceHttpWithHttpsInMavenURIs(TestMigrations):
    app_name = "minecode"
    migrate_from = "0026_set_is_visitable_for_maven_index_uris"
    migrate_to = "0027_replace_http_with_https_in_maven_uris"

    def setUpBeforeMigration(self, apps):
        # using get_model to avoid circular import
        ResourceURI = apps.get_model("minecode", "ResourceURI")

        self.resource_uris = [
            ResourceURI.objects.create(
                uri="http://repo1.maven.org/maven2/xyz/upperlevel/command/spigot/spigot-command-api/1.1.1/spigot-command-api-1.1.1.pom",
            ),
            ResourceURI.objects.create(
                uri="https://repo1.maven.org/maven2/xyz/upperlevel/command/spigot/spigot-command-api/1.1.1/spigot-command-api-1.1.1.pom",
            ),
        ]

        for resource_uri in self.resource_uris:
            resource_uri.save()

    def test_replace_http_with_https_in_maven_uris(self):
        # using get_model to avoid circular import
        ResourceURI = apps.get_model("minecode", "ResourceURI")
        results = list(
            ResourceURI.objects.values(
                "uri",
            ).all()
        )
        expected = [
            {
                "uri": "https://repo1.maven.org/maven2/xyz/upperlevel/command/spigot/spigot-command-api/1.1.1/spigot-command-api-1.1.1.pom"
            },
            {
                "uri": "https://repo1.maven.org/maven2/xyz/upperlevel/command/spigot/spigot-command-api/1.1.1/spigot-command-api-1.1.1.pom"
            },
        ]
        self.assertEqual(results, expected)
