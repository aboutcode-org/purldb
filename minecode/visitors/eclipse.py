#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from bs4 import BeautifulSoup

from commoncode import fileutils
from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class EclipseSeed(seed.Seeder):

    def get_seeds(self):
        yield 'http://projects.eclipse.org/json/projects/all'


@visit_router.route('https://projects.eclipse.org/list-of-projects')
class EclipseProjectVisitors(HttpVisitor):
    """
    Visit the HTML page of eclipse projects page and return the Packages info, json data and error.
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue
            href = a['href']
            if href and href.startswith('https://projects.eclipse.org/projects/'):
                # if the herf content starts with Eclipse single project suffix, generate a URI with the href content
                project_name = href.replace('https://projects.eclipse.org/projects/', '')
                package_url = PackageURL(type='eclipse', name=project_name).to_string()
                yield URI(uri=href, package_url=package_url, source_uri=self.uri)


@visit_router.route('https://projects.eclipse.org/projects/.*')
class EclipseSingleProjectVisitor(HttpVisitor):
    """
    Visit the HTML page of single eclipse project.
    This is to get the HTML page as metadata, as it's single project and the URI is already collected by
    EclipseProjectVisitors https://projects.eclipse.org/list-of-projects, so it won't return any new URI
    and the goal is to return HTML page.

    For example:https://projects.eclipse.org/projects/modeling.m2t.accele
    """
    pass


@visit_router.route('http://git.eclipse.org/c')
class EclipseGitVisitor(HttpVisitor):
    """
    Visitor Eclipse Git HTML page and return URIs in the Git HTML page.
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        for td in page.find_all(name='td'):
            if 'class' not in td.attrs:
                continue
            if td.attrs.get('class') != ['sublevel-repo']:
                continue

            for a in td.findChildren(name='a'):
                href = a['href']
                name = a.contents[0]
                package_url = PackageURL(type='eclipse', name=name).to_string()
                yield URI(uri=href, package_url=package_url, source_uri=self.uri)


@visit_router.route('http://www.eclipse.org/downloads/packages/all')
class EclipsePackagesVisitor(HttpVisitor):
    """
    Visit the Eclipse packages HTML page and return URIs parsed from HTML page.
    """

    def fetch(self, uri, timeout=40):
        """
        Fetch and return the content found at a remote uri with an extra timeout
        """
        return HttpVisitor.fetch(self, uri, timeout=timeout)

    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        for td in page.find_all(name='span'):
            if 'class' not in td.attrs:
                continue
            if td.attrs.get('class') != ['field-content']:
                continue

            a = td.find(name='a')
            href = a['href']
            name = a.contents[0]
            # Skip some of the nodes if it's a HTML tag but not a string
            if name and isinstance(name, str):
                package_url = PackageURL(type='eclipse', name=name).to_string()
                yield URI(uri=href, package_url=package_url, source_uri=self.uri)


@visit_router.route('http://www.eclipse.org/downloads/packages/release/.*')
class EclipseReleaseVisitor(HttpVisitor):
    """
    Visit the Eclipse release HTML page and return expected Package URIs.
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        suffix_list = ['-win32.zip', '-win64.exe', '-win32-x86_64.zip', '-linux-gtk-x86_64.tar.gz',
                       '-linux-gtk-x86_64.tar.gz', '-macosx-cocoa-x86_64.tar.gz', '-linux-gtk.tar.gz', '-x86_64.tar.gz']
        for div in page.find_all(name='div'):
            for a in div.find_all(name='a'):
                url = a.get('href')
                if url and 'download.php?file=' in url:
                    file_name = fileutils.file_name(url)
                    name = file_name
                    for suffix in suffix_list:
                        name = name.replace(suffix, '')
                    package_url = PackageURL(type='eclipse', name=name).to_string()
                    yield URI(uri=url, file_name=file_name, package_url=package_url, source_uri=self.uri)


@visit_router.route('http://projects.eclipse.org/json/projects/all')
class EclipseProjectsJsonVisitor(HttpJsonVisitor):
    """
    Visit the Ecipse json API and return expected project specified URIs.
    """

    def fetch(self, uri, timeout=40):
        """
        Fetch and return the content found at a remote uri with an extra timeout
        """
        return HttpJsonVisitor.fetch(self, uri, timeout=timeout)

    def get_uris(self, content):
        url_template = 'http://projects.eclipse.org/json/project/{name}'
        projects = content.get('projects', {})
        for project in projects:
            # TODO: are we sure there is not more data available in this JSON?
            package_url = PackageURL(type='eclipse', name=project).to_string()
            yield URI(uri=url_template.format(name=project), package_url=package_url, source_uri=self.uri)


@visit_router.route('http://projects.eclipse.org/json/project/.*')
class EclipseSingleProjectJsonVisitor(HttpJsonVisitor):
    """
    Visit json of a single Eclipse project. This is to return the json
    itself without any URIs, as the URI itself is returned by
    EclipseProjectsJsonVisitor.
    """
    pass
