import os
from unittest import mock
from unittest.mock import patch

from django.test import TestCase as DjangoTestCase

from packagedcode.maven import _parse
from packageurl import PackageURL

import packagedb
from minecode.collectors import maven
from minecode.tests import FIXTURES_REGEN
from minecode.utils_test import JsonBasedTesting


class MavenPriorityQueueTests(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "testfiles"
    )

    def setUp(self):
        super(MavenPriorityQueueTests, self).setUp()

        self.expected_pom_loc = self.get_test_loc("maven/pom/classworlds-1.1.pom")
        with open(self.expected_pom_loc) as f:
            self.expected_pom_contents = f.read()

        self.scan_package = _parse(
            "maven_pom",
            "maven",
            "Java",
            text=self.expected_pom_contents,
        )

    def test_get_pom_text(self, regen=FIXTURES_REGEN):
        pom_contents = maven.get_pom_text(
            namespace=self.scan_package.namespace,
            name=self.scan_package.name,
            version=self.scan_package.version,
        )
        if regen:
            with open(self.expected_pom_loc, "w") as f:
                f.write(pom_contents)
        self.assertEqual(self.expected_pom_contents, pom_contents)

        pom_contents = maven.get_pom_text(
            namespace="",
            name="does-not-exist",
            version="1.0",
        )
        self.assertFalse(pom_contents)

    def test_get_package_sha1(self):
        sha1 = maven.get_package_sha1(self.scan_package)
        expected_sha1 = "60c708f55deeb7c5dfce8a7886ef09cbc1388eca"
        self.assertEqual(expected_sha1, sha1)

    def test_map_maven_package(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        package_url = PackageURL.from_string(self.scan_package.purl)
        maven.map_maven_package(
            package_url, packagedb.models.PackageContentType.BINARY, ("test_pipeline")
        )
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_purl_str = "pkg:maven/classworlds/classworlds@1.1"
        self.assertEqual(expected_purl_str, package.purl)

    def test_map_maven_package_custom_repo_url(self):
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        custom_repo_purl = "pkg:maven/org.eclipse.core/runtime@20070801?repository_url=https://packages.atlassian.com/mvn/maven-atlassian-external/"
        package_url = PackageURL.from_string(custom_repo_purl)
        maven.map_maven_package(
            package_url, packagedb.models.PackageContentType.BINARY, ("test_pipeline")
        )
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(1, package_count)
        package = packagedb.models.Package.objects.all().first()
        expected_repo_url = "https://packages.atlassian.com/mvn/maven-atlassian-external//org/eclipse/core/runtime/20070801/runtime-20070801.jar"
        self.assertEqual(expected_repo_url, package.download_url)

    def test_process_request(self):
        purl_str = "pkg:maven/org.apache.twill/twill-core@0.12.0"
        download_url = "https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0.jar"
        purl_sources_str = f"{purl_str}?classifier=sources"
        sources_download_url = "https://repo1.maven.org/maven2/org/apache/twill/twill-core/0.12.0/twill-core-0.12.0-sources.jar"
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(0, package_count)
        maven.process_request(purl_str)
        package_count = packagedb.models.Package.objects.all().count()
        self.assertEqual(2, package_count)
        purls = [
            (package.purl, package.download_url)
            for package in packagedb.models.Package.objects.all()
        ]
        self.assertIn((purl_str, download_url), purls)
        self.assertIn((purl_sources_str, sources_download_url), purls)

    def test_fetch_parent(self, regen=FIXTURES_REGEN):
        pom_loc = self.get_test_loc("maven/pom/ant-antlr-1.10.1.pom")
        with open(pom_loc) as f:
            pom_text = f.read()
        parent_pom_text = maven.fetch_parent(pom_text)
        expected_loc = self.get_test_loc("maven/pom/ant-parent-1.10.1.pom")

        if regen:
            with open(expected_loc, "w") as f:
                f.write(parent_pom_text)

        with open(expected_loc) as f:
            expected_pom_text = f.read()
        self.assertEqual(expected_pom_text, parent_pom_text)

    def test_get_ancestry(self):
        pom_loc = self.get_test_loc("maven/pom/pulsar-client-1x-2.5.1.pom")
        with open(pom_loc) as f:
            pom_text = f.read()
        ancestor_pom_texts = list(maven.get_ancestry(pom_text))
        expected_ancestor_pom_texts = []
        for expected_loc in [
            self.get_test_loc("maven/pom/apache-18.pom"),
            self.get_test_loc("maven/pom/pulsar-2.5.1.pom"),
            self.get_test_loc("maven/pom/pulsar-client-1x-base-2.5.1.pom"),
        ]:
            with open(expected_loc) as f:
                expected_pom_text = f.read()
            expected_ancestor_pom_texts.append(expected_pom_text)
        self.assertEqual(expected_ancestor_pom_texts, ancestor_pom_texts)

    def test_merge_parent(self, regen=FIXTURES_REGEN):
        pom_loc = self.get_test_loc("maven/pom/ant-antlr-1.10.1.pom")
        with open(pom_loc) as f:
            pom_text = f.read()
        package = _parse("maven_pom", "maven", "Java", text=pom_text)
        expected_before_loc = self.get_test_loc(
            "maven/pom/ant-antlr-1.10.1-package_before.json"
        )
        self.check_expected_results(package.to_dict(), expected_before_loc, regen=regen)

        parent_pom_loc = self.get_test_loc("maven/pom/ant-parent-1.10.1.pom")
        with open(parent_pom_loc) as f:
            parent_pom_text = f.read()
        parent_package = _parse("maven_pom", "maven", "Java", text=parent_pom_text)
        package = maven.merge_parent(package, parent_package)
        expected_after_loc = self.get_test_loc(
            "maven/pom/ant-antlr-1.10.1-package_after.json"
        )
        self.check_expected_results(package.to_dict(), expected_after_loc, regen=regen)

    def test_merge_ancestors(self, regen=FIXTURES_REGEN):
        pom_loc = self.get_test_loc("maven/pom/pulsar-client-1x-2.5.1.pom")
        with open(pom_loc) as f:
            pom_text = f.read()
        package = _parse("maven_pom", "maven", "Java", text=pom_text)
        expected_before_loc = self.get_test_loc(
            "maven/pom/pulsar-client-1x-2.5.1-package_before.json"
        )
        self.check_expected_results(package.to_dict(), expected_before_loc, regen=regen)

        ancestor_pom_texts = []
        for loc in [
            self.get_test_loc("maven/pom/apache-18.pom"),
            self.get_test_loc("maven/pom/pulsar-2.5.1.pom"),
            self.get_test_loc("maven/pom/pulsar-client-1x-base-2.5.1.pom"),
        ]:
            with open(loc) as f:
                pom_text = f.read()
            ancestor_pom_texts.append(pom_text)

        maven.merge_ancestors(ancestor_pom_texts, package)
        expected_after_loc = self.get_test_loc(
            "maven/pom/pulsar-client-1x-2.5.1-package_after.json"
        )
        self.check_expected_results(package.to_dict(), expected_after_loc, regen=regen)

    @mock.patch("minecode.collectors.maven.get_pom_text")
    def test_get_merged_ancestor_package_from_maven_package(
        self, get_pom_text_mock, regen=FIXTURES_REGEN
    ):
        get_pom_text_mock.return_value = ""
        ancestor_pom_texts = []
        with patch("minecode.collectors.maven.get_ancestry") as mock_get_ancestry:
            for loc in [
                self.get_test_loc("maven/pom/apache-18.pom"),
                self.get_test_loc("maven/pom/pulsar-2.5.1.pom"),
                self.get_test_loc("maven/pom/pulsar-client-1x-base-2.5.1.pom"),
            ]:
                with open(loc) as f:
                    pom_text = f.read()
                ancestor_pom_texts.append(pom_text)
            mock_get_ancestry.return_value = ancestor_pom_texts
            db_package = packagedb.models.Package.objects.create(
                name="pulsar-client",
                namespace="org.apache.pulsar",
                version="2.5.1",
                type="maven",
                download_url="https://repo1.maven.org/maven2/org/apache/pulsar/pulsar-client/2.5.1/pulsar-client-2.5.1.jar",
            )
            merged_package = maven.get_merged_ancestor_package_from_maven_package(
                package=db_package
            )
            expected_loc = self.get_test_loc(
                "maven/pom/pulsar-client-merged-ancestor-package.json"
            )
            self.check_expected_results(
                merged_package.to_dict(), expected_loc, regen=regen
            )


class MavenCrawlerFunctionsTest(JsonBasedTesting, DjangoTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), "testfiles")

    def test_check_if_file_name_is_linked_on_page(self):
        links = ["foo/", "bar/", "baz/"]
        self.assertTrue(maven.check_if_file_name_is_linked_on_page("foo/", links))
        self.assertFalse(maven.check_if_file_name_is_linked_on_page("qux/", links))

    def test_check_if_page_has_pom_files(self):
        links1 = ["foo/", "bar.jar", "bar.pom"]
        links2 = ["foo/", "bar.jar"]
        self.assertTrue(maven.check_if_page_has_pom_files(links1))
        self.assertFalse(maven.check_if_page_has_pom_files(links2))

    def test_check_if_page_has_directories(self):
        links1 = ["foo/", "bar/", "baz/"]
        links2 = ["../", "bar.pom", "bar.jar"]
        self.assertTrue(maven.check_if_page_has_directories(links1))
        self.assertFalse(maven.check_if_page_has_directories(links2))

    def test_check_if_package_version_page(self):
        links1 = ["../", "bar.pom", "bar.jar"]
        links2 = ["../", "foo/", "bar/", "baz/"]
        self.assertTrue(maven.check_if_package_version_page(links1))
        self.assertFalse(maven.check_if_package_version_page(links2))

    def test_check_if_package_page(self):
        links1 = ["../", "maven-metadata.xml"]
        links2 = ["../", "bar.pom", "bar.jar"]
        self.assertTrue(maven.check_if_package_page(links1))
        self.assertFalse(maven.check_if_package_page(links2))

    def test_check_if_maven_root(self):
        links1 = ["../", "archetype-catalog.xml"]
        links2 = ["../", "bar.pom", "bar.jar"]
        self.assertTrue(maven.check_if_maven_root(links1))
        self.assertFalse(maven.check_if_maven_root(links2))

    @mock.patch("requests.get")
    def test_check_on_page(self, mock_request_get):
        checker = maven.check_if_page_has_pom_files
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="parent-7.11.0.pom" title="parent-7.11.0.pom">parent-7.11.0.pom</a>'
        self.assertTrue(
            maven.check_on_page(
                "https://repo1.maven.org/maven2/net/shibboleth/parent/7.11.0/", checker
            )
        )

    @mock.patch("requests.get")
    def test_is_maven_root(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="archetype-catalog.xml" title="archetype-catalog.xml">archetype-catalog.xml</a>'
        self.assertTrue(maven.is_maven_root("https://repo1.maven.org/maven2/"))

    @mock.patch("requests.get")
    def test_is_package_page(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="maven-metadata.xml" title="maven-metadata.xml">maven-metadata.xml</a>'
        self.assertTrue(
            maven.is_package_page("https://repo1.maven.org/maven2/xml-apis/xml-apis/")
        )

    @mock.patch("requests.get")
    def test_is_package_version_page(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = """
        <a href="../" title="../">../</a>
        <a href="parent-7.11.0.pom" title="parent-7.11.0.pom">parent-7.11.0.pom</a>
        """
        self.assertTrue(
            maven.is_package_version_page(
                "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/"
            )
        )

    def test_url_parts(self):
        url = "https://example.com/foo/bar/baz.jar"
        scheme, netloc, path_segments = maven.url_parts(url)
        self.assertEqual("https", scheme)
        self.assertEqual("example.com", netloc)
        self.assertEqual(["foo", "bar", "baz.jar"], path_segments)

    def test_create_url(self):
        scheme = "https"
        netloc = "example.com"
        path_segments = ["foo", "bar", "baz.jar"]
        url = "https://example.com/foo/bar/baz.jar"
        self.assertEqual(url, maven.create_url(scheme, netloc, path_segments))

    @mock.patch("requests.get")
    def test_get_maven_root(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = '<a href="archetype-catalog.xml" title="archetype-catalog.xml">archetype-catalog.xml</a>'
        self.assertEqual(
            "https://repo1.maven.org/maven2",
            maven.get_maven_root(
                "https://repo1.maven.org/maven2/net/shibboleth/parent/7.11.0/"
            ),
        )

    @mock.patch("requests.get")
    def test_determine_namespace_name_version_from_url(self, mock_request_get):
        url = "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2"
        root_url = "https://repo1.maven.org/maven2"

        package_page_text = """
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                           2005-09-20 05:53         -
        <a href="maven-metadata.xml" title="maven-metadata.xml">maven-metadata.xml</a>
                                2012-06-26 17:01       567
        """
        package_page = mock.Mock(ok=True, text=package_page_text)

        package_version_page_text = """
        <a href="../">../</a> -
        <a href="xml-apis-1.0.b2.pom" title="xml-apis-1.0.b2.pom">xml-apis-1.0.b2.pom</a>
                               2005-09-20 05:53      2249
        """
        package_version_page = mock.Mock(ok=True, text=package_version_page_text)
        mock_request_get.side_effect = [
            mock.Mock(ok=True, text=""),
            mock.Mock(ok=True, text=""),
            package_page,
            mock.Mock(ok=True, text=""),
            package_version_page,
        ]

        namespace, package_name, package_version = (
            maven.determine_namespace_name_version_from_url(url, root_url)
        )
        self.assertEqual("xml-apis", namespace)
        self.assertEqual("xml-apis", package_name)
        self.assertEqual("1.0.b2", package_version)

    @mock.patch("requests.get")
    def test_add_to_import_queue(self, mock_request_get):
        from minecode.models import ImportableURI

        url = "https://repo1.maven.org/maven2/xml-apis/xml-apis/"
        root_url = "https://repo1.maven.org/maven2"

        package_page_text = """
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                           2005-09-20 05:53         -
        <a href="maven-metadata.xml" title="maven-metadata.xml">maven-metadata.xml</a>
                                2012-06-26 17:01       567
        """
        package_page = mock.Mock(ok=True, text=package_page_text)

        package_version_page_text = """
        <a href="../">../</a> -
        <a href="xml-apis-1.0.b2.pom" title="xml-apis-1.0.b2.pom">xml-apis-1.0.b2.pom</a>
                               2005-09-20 05:53      2249
        """
        package_version_page = mock.Mock(ok=True, text=package_version_page_text)
        mock_request_get.side_effect = [
            package_page,
            mock.Mock(ok=True, text=""),
            mock.Mock(ok=True, text=""),
            package_page,
            mock.Mock(ok=True, text=""),
            package_version_page,
        ]

        self.assertEqual(0, ImportableURI.objects.all().count())
        maven.add_to_import_queue(url, root_url)
        self.assertEqual(1, ImportableURI.objects.all().count())
        importable_uri = ImportableURI.objects.get(uri=url)
        self.assertEqual("pkg:maven/xml-apis/xml-apis", importable_uri.package_url)

    def test_filter_only_directories(self):
        timestamps_by_links = {
            "../": "-",
            "foo/": "-",
            "foo.pom": "2023-09-28",
        }
        expected = {
            "foo/": "-",
        }
        self.assertEqual(expected, maven.filter_only_directories(timestamps_by_links))

    def test_filter_for_artifacts(self):
        timestamps_by_links = {
            "../": "2023-09-28",
            "foo.pom": "2023-09-28",
            "foo.ejb3": "2023-09-28",
            "foo.ear": "2023-09-28",
            "foo.aar": "2023-09-28",
            "foo.apk": "2023-09-28",
            "foo.gem": "2023-09-28",
            "foo.jar": "2023-09-28",
            "foo.nar": "2023-09-28",
            "foo.so": "2023-09-28",
            "foo.swc": "2023-09-28",
            "foo.tar": "2023-09-28",
            "foo.tar.gz": "2023-09-28",
            "foo.war": "2023-09-28",
            "foo.xar": "2023-09-28",
            "foo.zip": "2023-09-28",
        }
        expected = {
            "foo.ejb3": "2023-09-28",
            "foo.ear": "2023-09-28",
            "foo.aar": "2023-09-28",
            "foo.apk": "2023-09-28",
            "foo.gem": "2023-09-28",
            "foo.jar": "2023-09-28",
            "foo.nar": "2023-09-28",
            "foo.so": "2023-09-28",
            "foo.swc": "2023-09-28",
            "foo.tar": "2023-09-28",
            "foo.tar.gz": "2023-09-28",
            "foo.war": "2023-09-28",
            "foo.xar": "2023-09-28",
            "foo.zip": "2023-09-28",
        }
        self.assertEqual(expected, maven.filter_for_artifacts(timestamps_by_links))

    def test_collect_links_from_text(self):
        filter = maven.filter_only_directories
        text = """
        <a href="../">../</a>
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                                   2005-09-20 05:53         -
        <a href="1.2.01/" title="1.2.01/">1.2.01/</a>
                                                   2010-02-03 21:05         -
        """
        expected = {"1.0.b2/": "2005-09-20 05:53", "1.2.01/": "2010-02-03 21:05"}
        self.assertEqual(expected, maven.collect_links_from_text(text, filter=filter))

    def test_create_absolute_urls_for_links(self):
        filter = maven.filter_only_directories
        text = """
        <a href="../">../</a>
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                                   2005-09-20 05:53         -
        <a href="1.2.01/" title="1.2.01/">1.2.01/</a>
                                                   2010-02-03 21:05         -
        """
        url = "https://repo1.maven.org/maven2/xml-apis/xml-apis/"
        expected = {
            "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/": "2005-09-20 05:53",
            "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.2.01/": "2010-02-03 21:05",
        }
        self.assertEqual(
            expected, maven.create_absolute_urls_for_links(text, url, filter=filter)
        )

    @mock.patch("requests.get")
    def test_get_directory_links(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = """
        <a href="../">../</a>
        <a href="1.0.b2/" title="1.0.b2/">1.0.b2/</a>
                                                   2005-09-20 05:53         -
        <a href="1.2.01/" title="1.2.01/">1.2.01/</a>
                                                   2010-02-03 21:05         -
        """
        url = "https://repo1.maven.org/maven2/xml-apis/xml-apis/"
        expected = {
            "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/": "2005-09-20 05:53",
            "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.2.01/": "2010-02-03 21:05",
        }
        self.assertEqual(expected, maven.get_directory_links(url))

    @mock.patch("requests.get")
    def test_get_artifact_links(self, mock_request_get):
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = """
        <a href="../">../</a>
        <a href="xml-apis-1.0.b2.jar" title="xml-apis-1.0.b2.jar">xml-apis-1.0.b2.jar</a>
                               2005-09-20 05:53    109318
        <a href="xml-apis-1.0.b2.pom" title="xml-apis-1.0.b2.pom">xml-apis-1.0.b2.pom</a>
                               2005-09-20 05:53      2249
        """
        url = "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/"
        expected = {
            "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/xml-apis-1.0.b2.jar": "2005-09-20 05:53",
        }
        self.assertEqual(expected, maven.get_artifact_links(url))

    def test_crawl_to_package(self):
        pass

    def test_crawl_maven_repo_from_root(self):
        pass

    @mock.patch("requests.get")
    def test_get_artifact_sha1(self, mock_request_get):
        sha1 = "3136ca936f64c9d68529f048c2618bd356bf85c9"
        mock_request_get.return_value.ok = True
        mock_request_get.return_value.text = sha1
        self.assertEqual(
            sha1,
            maven.get_artifact_sha1(
                "https://repo1.maven.org/maven2/xml-apis/xml-apis/1.0.b2/xml-apis-1.0.b2.jar.sha1"
            ),
        )

    def test_get_classifier_from_artifact_url(self):
        artifact_url = "https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/livereload-jvm-0.2.0-onejar.jar"
        package_version_page_url = (
            "https://repo1.maven.org/maven2/net/alchim31/livereload-jvm/0.2.0/"
        )
        package_name = "livereload-jvm"
        package_version = "0.2.0"
        classifier = maven.get_classifier_from_artifact_url(
            artifact_url, package_version_page_url, package_name, package_version
        )
        self.assertEqual("onejar", classifier)
