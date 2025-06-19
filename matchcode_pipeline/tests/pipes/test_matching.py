import io
import uuid
from pathlib import Path

from django.test import TestCase

from scanpipe import pipes
from scanpipe.models import Project
from scanpipe.pipes import flag
from scanpipe.pipes.input import copy_inputs
from scanpipe.tests import make_resource_directory
from scanpipe.tests import make_resource_file
from scanpipe.tests import package_data1
from scanpipe.tests import package_data2

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateResourceContentIndex
from matchcode_pipeline.pipes import matching
from packagedb.models import Package
from packagedb.models import Resource


class MatchingPipesTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"
    databases = {"packagedb", "default"}

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")
        self.package1 = Package.objects.create(
            type=package_data1["type"],
            namespace=package_data1["namespace"],
            name=package_data1["name"],
            version=package_data1["version"],
            sha1="abcdef",
        )
        self.directory_content_fingerprint1 = ApproximateDirectoryContentIndex.index(
            fingerprint="00000003238f6ed2c218090d4da80b3b42160e69",
            resource_path="package.jar-extract",
            package=self.package1,
        )
        self.directory1 = Resource.objects.create(
            path="package.jar-extract",
            package=self.package1,
        )
        self.resource1 = Resource.objects.create(
            path="inflate.c", size=55466, package=self.package1
        )
        self.resource_content_fingerprint1 = ApproximateResourceContentIndex.index(
            fingerprint="000018fba23a49e4cd40718d1297be719e6564a4",
            resource_path="inflate.c",
            package=self.package1,
        )

    def test_matchcode_pipeline_pipes_matching_get_project_resources_qs(self):
        package_resource = make_resource_file(self.project1, "package.jar", is_archive=True)
        make_resource_directory(self.project1, "package.jar-extract/")
        make_resource_file(self.project1, "package.jar-extract/foo.class")

        directory_resource = make_resource_directory(self.project1, "directory1")
        make_resource_file(self.project1, "directory1/foo.txt")

        # This directory and its contents should not be returned
        make_resource_directory(self.project1, "directory100")
        make_resource_file(self.project1, "directory100/bar.txt")

        resources = [package_resource, directory_resource]
        resources_qs = matching.get_project_resources_qs(self.project1, resources=resources)
        expected_paths = [
            "package.jar",
            "package.jar-extract/",
            "package.jar-extract/foo.class",
            "directory1",
            "directory1/foo.txt",
        ]
        expected_qs = self.project1.codebaseresources.filter(path__in=expected_paths)
        self.assertQuerySetEqual(expected_qs, resources_qs)

    def test_matchcode_pipeline_pipes_matching_match_purldb_resources(self):
        to_1 = make_resource_file(self.project1, "package.jar", sha1="abcdef")
        to_1.is_archive = True
        to_1.save()
        # The initial status will be updated to flag.MATCHED_TO_PURLDB_PACKAGE
        to_2 = make_resource_file(self.project1, "package.jar-extract/a.class", status=flag.MAPPED)
        to_3 = make_resource_file(self.project1, "package.jar-extract/b.class")

        buffer = io.StringIO()
        matching.match_purldb_resources(
            self.project1,
            matcher_func=matching.match_purldb_package,
            archives_only=True,
            logger=buffer.write,
        )
        expected = (
            "Matching 1 resources in PurlDB, using SHA13 resources matched in PurlDB using 1 SHA1s"
        )
        self.assertEqual(expected, buffer.getvalue())

        package = self.project1.discoveredpackages.get()
        self.assertEqual(package_data1["name"], package.name)

        for resource in [to_1, to_2, to_3]:
            resource.refresh_from_db()
            self.assertEqual(flag.MATCHED_TO_PURLDB_PACKAGE, resource.status)
            self.assertEqual(package, resource.discovered_packages.get())

    def test_matchcode_pipeline_pipes_matching_match_purldb_directories(self):
        to_1 = make_resource_directory(
            self.project1,
            "package.jar-extract",
            extra_data={"directory_content": "00000003238f6ed2c218090d4da80b3b42160e69"},
        )
        to_2 = make_resource_file(self.project1, "package.jar-extract/a.class")
        to_3 = make_resource_file(self.project1, "package.jar-extract/b.class")

        buffer = io.StringIO()
        matching.match_purldb_directories(
            self.project1,
            logger=buffer.write,
        )

        expected = "Matching 1 directory against PurlDB1 directory matched in PurlDB"
        self.assertEqual(expected, buffer.getvalue())

        package = self.project1.discoveredpackages.get()
        self.assertEqual(package_data1["name"], package.name)

        for resource in [to_1, to_2, to_3]:
            resource.refresh_from_db()
            self.assertEqual("matched-to-purldb-directory", resource.status)
            self.assertEqual(package, resource.discovered_packages.get())

    def test_matchcode_pipeline_pipes_matching_match_purldb_resources_post_process(
        self,
    ):
        to_map = self.data_location / "d2d-javascript" / "to" / "main.js.map"
        to_mini = self.data_location / "d2d-javascript" / "to" / "main.js"
        to_dir = (
            self.project1.codebase_path / "project.tar.zst/modules/apps/adaptive-media/"
            "adaptive-media-web-extract/src/main/resources/META-INF/resources/"
            "adaptive_media/js"
        )
        to_dir.mkdir(parents=True)
        copy_inputs([to_map, to_mini], to_dir)

        pipes.collect_and_create_codebase_resources(self.project1)

        resources = self.project1.codebaseresources.filter(
            path__startswith=(
                "project.tar.zst/modules/apps/adaptive-media/"
                "adaptive-media-web-extract/src/main/resources/META-INF/resources/"
                "adaptive_media/js/main.js"
            )
        )

        mini_resource = self.project1.codebaseresources.filter(
            path=(
                "project.tar.zst/modules/apps/adaptive-media/"
                "adaptive-media-web-extract/src/main/resources/META-INF/resources/"
                "adaptive_media/js/main.js"
            )
        )

        dummy_package_data1 = package_data1.copy()
        dummy_package_data1["uuid"] = uuid.uuid4()
        package1, _ = matching.create_package_from_purldb_data(
            self.project1,
            resources,
            dummy_package_data1,
            flag.MATCHED_TO_PURLDB_RESOURCE,
        )

        dummy_package_data2 = package_data2.copy()
        dummy_package_data2["uuid"] = uuid.uuid4()
        package2, _ = matching.create_package_from_purldb_data(
            self.project1,
            mini_resource,
            dummy_package_data2,
            flag.MATCHED_TO_PURLDB_RESOURCE,
        )

        buffer = io.StringIO()
        matching.match_purldb_resources_post_process(
            self.project1,
            logger=buffer.write,
        )
        expected = f"Refining matching for 1 {flag.MATCHED_TO_PURLDB_RESOURCE} archives."
        self.assertIn(expected, buffer.getvalue())

        package1_resource_count = package1.codebase_resources.count()
        package2_resource_count = package2.codebase_resources.count()

        self.assertEqual(2, package1_resource_count)
        self.assertEqual(0, package2_resource_count)

    def test_matchcode_pipeline_pipes_matching_match_purldb_resource_approximately(
        self,
    ):
        resource = make_resource_file(
            self.project1,
            "inflate.c",
            size=55466,
            extra_data={"halo1": "000018f4aa3a49e4cd40718d1297be519e6564a4"},
        )

        buffer = io.StringIO()
        matching.match_purldb_resources_approximately(
            self.project1,
            logger=buffer.write,
        )

        expected = (
            "Approximate matching 1 resource against PurlDB"
            "1 resource approximately matched in PurlDB"
        )
        self.assertEqual(expected, buffer.getvalue())

        package = self.project1.discoveredpackages.get()
        self.assertEqual(package_data1["name"], package.name)

        resource.refresh_from_db()
        self.assertEqual("approximate-matched-to-purldb-resource", resource.status)
        self.assertEqual(package, resource.discovered_packages.get())

    def test_matching_create_package_from_purldb_data_set_package_match_type(self):
        resource = make_resource_file(self.project1, "package.jar-extract/a.class")
        resources = [resource]
        dummy_package_data1 = package_data1.copy()
        package1, _ = matching.create_package_from_purldb_data(
            self.project1,
            resources,
            dummy_package_data1,
            flag.MATCHED_TO_PURLDB_RESOURCE,
        )
        self.assertEqual(flag.MATCHED_TO_PURLDB_RESOURCE, package1.extra_data["matchcodeio_match_status"])
