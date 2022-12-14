#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import codecs
import json
import xmlrpc

from packageurl import PackageURL

from discovery import seed
from discovery import visit_router
from discovery.utils import get_temp_file
from discovery.visitors import HttpJsonVisitor
from discovery.visitors import URI
from discovery.visitors import Visitor


"""
Visitors for Pypi and Pypi-like Python package repositories.

We have this hierarchy in Pypi:
    index (xmlrpc) -> packages (json) -> package releases (json) -> download urls

Pypi serves a main index via XMLRPC that contains a list of package names.
For each package, a JSON contains details including the list of all releases.
For each release, a JSON contains details for the released version and all the
downloads available for this release. We create Packages at this level as well
as one download URI for each effective download.

Some information about every release and download is replicated in every JSON
payload and is ignored for simplicity (which is not super efficient).
"""


class PypiSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://pypi.python.org/pypi/'


@visit_router.route('https://pypi.python.org/pypi/')
class PypiIndexVisitor(Visitor):
    """
    Collect package metadata URIs from the top level pypi index for each package.
    """
    def fetch(self, uri, timeout=None):
        """
        Specialized fetching using XML RPCs.
        """
        packages = xmlrpc.client.ServerProxy(uri).list_packages()
        content = list(packages)

        temp_file = get_temp_file('PypiIndexVisitor')
        with codecs.open(temp_file, mode='wb', encoding='utf-8') as expect:
            json.dump(content, expect, indent=2, separators=(',', ':'))
        return temp_file

    def dumps(self, content):
        """
        The content is huge json and should not be dumped.
        """
        return None

    def get_uris(self, content):
        with codecs.open(content, mode='rb', encoding='utf-8') as contentfile:
            packages_list = json.load(contentfile)

            url_template = 'https://pypi.python.org/pypi/{name}/json'
            for name in packages_list:
                package_url = PackageURL(type='pypi', name=name).to_string()
                yield URI(uri=url_template.format(name=name), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://pypi.python.org/pypi/[^/]+/json')
class PypiPackageVisitor(HttpJsonVisitor):
    """
    Collect package metadata URIs for all release of a single Pypi package.
    The url will contain only the package name, for example: https://pypi.org/pypi/vmock/json
    By parsing the content, the goal is to form the json with version/release: https://pypi.org/pypi/vmock/0.1/json
    """
    def get_uris(self, content):

        url_template = 'https://pypi.python.org/pypi/{name}/{release}/json'
        info = content.get('info', {})
        name = info.get('name')
        if name:
            for release in content['releases']:
                package_url = PackageURL(type='pypi', name=name, version=release).to_string()
                yield URI(uri=url_template.format(name=name, release=release), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://pypi.python.org/pypi/[^/]+/[^/]+/json')
class PypiPackageReleaseVisitor(HttpJsonVisitor):
    """
    Collect package download URIs for all packages archives of one Pypi package
    release. The example is: https://pypi.org/pypi/vmock/0.1/json
    """
    def get_uris(self, content):
        # TODO: this is likely best ignored entirely???
        # A download_url may be provided for an off-Pypi-download
        info = content.get('info', {})
        name = info.get('name')
        version = None
        download_url = info.get('download_url')
        if download_url and download_url != 'UNKNOWN':
            version = info.get('version')
            package_url = PackageURL(type='pypi', name=name, version=version).to_string()
            yield URI(uri=download_url, package_url=package_url, source_uri=self.uri)

        # Common on-Pypi-download URLs are in the urls block
        for download in content.get('urls', {}):
            url = download.get('url')
            if not url:
                continue
            package_url = PackageURL(type='pypi', name=name, version=version).to_string()
            yield URI(url, package_url=package_url, file_name=download.get('filename'),
                      size=download.get('size'), date=download.get('upload_time'),
                      md5=download.get('md5_digest'), source_uri=self.uri)
