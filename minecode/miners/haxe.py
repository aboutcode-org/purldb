#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from bs4 import BeautifulSoup
from packagedcode.haxe import HaxelibJsonHandler
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import HttpVisitor
from minecode.miners import Mapper


class HaxeSeed(seed.Seeder):
    is_active = False

    def get_seeds(self):
        yield "https://lib.haxe.org/all"


@visit_router.route("https://lib.haxe.org/all")
class HaxeProjectsVisitor(HttpVisitor):
    """Visit the Haxe all projects page and yield uri of each project."""

    def get_uris(self, content):
        """
        Parse the HTML to get project name, and format the url with this project name into a version URL.
        For example: https://lib.haxe.org/p/openfl/versions/
        """
        version_url_tempalte = "https://lib.haxe.org{project_href}versions"
        page = BeautifulSoup(content, "lxml")
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue
            href = a["href"]
            if href and href.startswith("/p/"):
                project_name = href.replace("/p", "").rstrip("/")
                package_url = PackageURL(type="haxe", name=project_name).to_string()
                yield URI(
                    uri=version_url_tempalte.format(project_href=href),
                    package_url=package_url,
                    source_uri=self.uri,
                )


@visit_router.route(r"https://lib.haxe.org/p/[\w\-\.]+/versions")
class HaxeVersionsVisitor(HttpVisitor):
    """
    Visit the version page of a project and yield uri of each version.
    For example: https://lib.haxe.org/p/openfl/versions
    """

    def get_uris(self, content):
        """Yield haxelib json URL based on specified version, for example: https://lib.haxe.org/p/openfl/8.6.4/raw-files/openfl/package.json"""
        version_url_tempalte = (
            "https://lib.haxe.org/p/{project}/{version}/raw-files/{project}/package.json"
        )
        page = BeautifulSoup(content, "lxml")
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue
            href = a["href"]
            if href and href.startswith("/p/") and href.endswith("/"):
                # Parse if the href contains the versino info: <a href="/p/openfl/8.6.3/">
                project_version = href.replace("/p/", "").rstrip("/")
                project_version = project_version.split("/")
                if len(project_version) == 2:
                    # if there is only one slash between project and version, openfl/8.6.3
                    project = project_version[0]
                    version = project_version[1]
                    package_url = PackageURL(type="haxe", name=project, version=version).to_string()
                    yield URI(
                        uri=version_url_tempalte.format(project=project, version=version),
                        package_url=package_url,
                        source_uri=self.uri,
                    )


@visit_router.route(r"https://lib.haxe.org/p/[\w\-\.]+/[\w\-\.]+/raw-files/[\w\-\.]+/package.json")
class HaxePackageJsonVisitor(HttpJsonVisitor):
    """Empty Visitor to get the package json content only."""

    pass


@map_router.route(r"https://lib.haxe.org/p/[\w\-\.]+/[\w\-\.]+/raw-files/[\w\-\.]+/package.json")
class HaxePackageJsonMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """Yield Package built from package json file."""
        # FIXME: JSON deserialization should be handled eventually by the framework
        metadata = json.loads(resource_uri.data)
        return build_packages_with_json(metadata, resource_uri.package_url)


def build_packages_with_json(metadata, purl=None):
    # yield package by getting package from the build_package parser in scancode
    package = HaxelibJsonHandler._parse(json_data=metadata)
    if package:
        package.set_purl(purl)
        yield package
