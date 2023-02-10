#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals


from bs4 import BeautifulSoup

from commoncode import fileutils
from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class NugetSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://api-v2v3search-0.nuget.org/query'
        yield 'https://www.nuget.org/packages?page=1'


@visit_router.route('https://api-v2v3search-0.nuget.org/query')
class NugetQueryVisitor(HttpJsonVisitor):
    """
     'https://api-v2v3search-0.nuget.org/query' is a query URL which has metadata for
     Nuget packages and we can query for all the packages by using the pagination
     technique. For example 'https://api-v2v3search-0.nuget.org/query?skip=40' will
     skip the first 40 packages in the order and returns JSON data for the packages
     from 40-60.
     'https://api-v2v3search-0.nuget.org/query' could be the latest version, as the
     url 'https://api-v3search-0.nuget.org/query' is not accessible now.
    """
    def get_uris(self, content):
        """
        Return all the URLs for query results through pagination.
        Starts with number '0', increment count by '20'.
        The total count is found by 'totalHits'.
        """
        pkgs_count = content.get('totalHits', 0)
        count = 0
        url_template = 'https://api-v2v3search-0.nuget.org/query?skip={count}'
        while count < pkgs_count:
            url = url_template.format(count=str(count))
            yield URI(uri=url, source_uri=self.uri)
            count = count + 20


@visit_router.route('https://api-v2v3search-0.nuget.org/query\?skip=\d+')
class PackagesPageVisitor(HttpJsonVisitor):
    """
    Visit the nuget API resources and return all the package URLs available at the passing`uri`.
    """
    def get_uris(self, content):
        metadata = content['data']
        for packages in metadata:
            for version in packages['versions']:
                pkg_ver = version['version']
                pkg_url = version['@id']
                version_template = '{pkg_version}.0.json'
                version_name = version_template.format(pkg_version=pkg_ver)
                name = pkg_url.replace('https://api.nuget.org/v3/registration1/', '').partition('/')[0]
                package_url = PackageURL(type='nuget', name=name, version=pkg_ver).to_string()
                if version_name in pkg_url:
                    # sometimes an extra '0' is appended to the version in the URL
                    # FIXME: this is weird: there must be good reason why this is done???
                    pkg_url = pkg_url.replace(version_name, pkg_ver + '.json')
                yield URI(uri=pkg_url, package_url=package_url, source_uri=self.uri)

                # Add another case to have registration0 or registration1 in the url, yield the alternative url.
                if pkg_url.find('/registration0/') > 0:
                    pkg_url = pkg_url.replace('/registration0/', '/registration1/')
                    yield URI(uri=pkg_url, source_uri=self.uri)

                elif pkg_url.find('/registration1/') > 0:
                    pkg_url = pkg_url.replace('/registration1/', '/registration0/')
                    yield URI(uri=pkg_url, source_uri=self.uri)


@visit_router.route('https://api.nuget.org/.+.json')
class NugetAPIJsonVisitor(HttpJsonVisitor):
    """
    Visit packageContent of nuget API json  and return a
    download URL for the NugetPackage object

    This could cover three cases:
    1. packageContent is not empty.
    https://api.nuget.org/v3/registration1/entityframework/4.3.1.json
    Visiting above link will return the npkg file: https://api.nuget.org/packages/entityframework.4.3.1.nupkg
     and return the json resource for next DownloadVisitor: https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json

    2. catalogEntry is not empty
    https://api.nuget.org/v3/registration1/entityframework/4.3.1.json
    Visiting above link will return the npkg file: https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json

    3. No key matched
    The second loop will return the url https://api.nuget.org/v3/catalog0/data/2015.02.07.22.31.06/entityframework.4.3.1.json
    by visiting this url it won't create any new uris, the key is to store the json file itself through visitor and used in mapper.
    """
    def get_uris(self, content):
        download_url = content.get('packageContent')
        if download_url:
            filename = fileutils.file_name(download_url)
            withou_prefix = filename.replace('.nupkg', '')
            filename_splits = withou_prefix.partition('.')
            name = filename_splits[0]
            version = None
            if len(filename_splits) > 1:
                version = filename_splits[-1]
            package_url = PackageURL(
                type='nuget',
                name=name,
                version=version)
            yield URI(uri=download_url, package_url=package_url, source_uri=self.uri)

        catalog_entry_url = content.get('catalogEntry')
        if catalog_entry_url:
            yield URI(uri=catalog_entry_url, source_uri=self.uri)


@visit_router.route('https://www.nuget.org/packages\?page=\d+')
class NugetHTMLPageVisitor(HttpVisitor):
    """
    Visitor to yield the URI of the each package page.
    """
    def get_uris(self, content):
        url_format = 'https://www.nuget.org/packages/{name}'
        soup = BeautifulSoup(content, 'lxml')
        has_package = False
        for a in soup.find_all('a'):
            if a.get('class') and 'package-title' in a.get('class'):
                has_package = True
                href = a.get('href')
                if not href:
                    continue
                # href format is like: "/packages/NUnit/"
                name = href.strip('/').partition('/')[-1]
                if name:
                    yield URI(uri=url_format.format(name=name), source_uri=self.uri)
        if has_package:
            page_id = self.uri.replace('https://www.nuget.org/packages?page=', '').strip('/')
            next_pageid = int(page_id) + 1
            nextpage_url_format = 'https://www.nuget.org/packages?page={id}'
            yield URI(uri=nextpage_url_format.format(id=next_pageid), source_uri=self.uri)


@visit_router.route('https://www.nuget.org/packages/[\w\-\.]+',
                    'https://www.nuget.org/packages/[\w\-\.]+/[\w\-\.]+')
class NugetHTMLPackageVisitor(HttpVisitor):
    """
    Visitor to fetch the package HTML content
    Example: https://www.nuget.org/packages/log4net
             or https://www.nuget.org/packages/log4net/2.0.7
    """
    pass
