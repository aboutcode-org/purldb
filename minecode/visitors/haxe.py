#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from bs4 import BeautifulSoup

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class HaxeSeed(seed.Seeder):
    is_active = False

    def get_seeds(self):
        yield 'https://lib.haxe.org/all'


@visit_router.route('https://lib.haxe.org/all')
class HaxeProjectsVisitor(HttpVisitor):
    """
    Visit the Haxe all projects page and yield uri of each project.
    """

    def get_uris(self, content):
        """
        Parse the HTML to get project name, and format the url with this project name into a version URL.
        For example: https://lib.haxe.org/p/openfl/versions/
        """
        version_url_tempalte = 'https://lib.haxe.org{project_href}versions'
        page = BeautifulSoup(content, 'lxml')
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue
            href = a['href']
            if href and href.startswith('/p/'):
                project_name = href.replace('/p', '').rstrip('/')
                package_url = PackageURL(type='haxe', name=project_name).to_string()
                yield URI(uri=version_url_tempalte.format(project_href=href), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://lib.haxe.org/p/[\w\-\.]+/versions')
class HaxeVersionsVisitor(HttpVisitor):
    """
    Visit the version page of a project and yield uri of each version.
    For example: https://lib.haxe.org/p/openfl/versions
    """

    def get_uris(self, content):
        """
        Yield haxelib json URL based on specified version, for example: https://lib.haxe.org/p/openfl/8.6.4/raw-files/openfl/package.json
        """
        version_url_tempalte = 'https://lib.haxe.org/p/{project}/{version}/raw-files/{project}/package.json'
        page = BeautifulSoup(content, 'lxml')
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue
            href = a['href']
            if href and href.startswith('/p/') and href.endswith('/'):
                # Parse if the href contains the versino info: <a href="/p/openfl/8.6.3/">
                project_version = href.replace('/p/', '').rstrip('/')
                project_version = project_version.split('/')
                if len(project_version) == 2:
                    # if there is only one slash between project and version, openfl/8.6.3
                    project = project_version[0]
                    version = project_version[1]
                    package_url = PackageURL(type='haxe', name=project, version=version).to_string()
                    yield URI(uri=version_url_tempalte.format(project=project, version=version), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://lib.haxe.org/p/[\w\-\.]+/[\w\-\.]+/raw-files/[\w\-\.]+/package.json')
class HaxePackageJsonVisitor(HttpJsonVisitor):
    """
    Empty Visitor to get the package json content only.
    """
    pass
