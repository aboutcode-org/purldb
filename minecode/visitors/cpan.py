#
# Copyright (c) by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import json

from bs4 import BeautifulSoup
from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class CpanSeed(seed.Seeder):

    def get_seeds(self):
        yield 'http://www.cpan.org/modules/01modules.index.html'
        author_search_template = 'https://fastapi.metacpan.org/author/_search?q=email:{char}*&size=5000'
        for char in 'abcdefghijklmnopqrstuvwxyz'.split():
            yield author_search_template.format(char)

# The idea of CPAN API visitor is based on
# https://github.com/metacpan/metacpan-api/blob/master/docs/API-docs.md
#
# From the doc: You can certainly scroll if you are fetching less than 5,000
# items. You might want to do this if you are expecting a large data set, but
# will still need to run many requests to get all of the required data.
#
# To get all results for sure it's over 5000, we should use search twice based
# on author and release.
#
# First get all authors by searching email from a-z, then get all releases based
# on each author. It will make the returned result a small set.

# For example:

# First try to reach the author search, the following search URL will get all
# authors whose email starts with 'a', this will loop from 'a' to 'z.

# https://fastapi.metacpan.org/author/_search?q=email:a*&size=5000

# If we get the Author ID in above returned json, we can pass to release search
# URL as follows, it will get all releases from the passing author.

# https://fastapi.metacpan.org/release/_search?q=author:ABERNDT&size=5000


@visit_router.route('https://fastapi.metacpan.org/author/_search\?q=email:[a-z]\*&size=5000')
class MetaCpanAuthorURLVisitors(HttpJsonVisitor):
    """
    Run search on author's email, and parse the returned json content and form
    the MetaCpanRleaseURLVisitors' URL by adding AUTHOR condition. For example:
    https://fastapi.metacpan.org/author/_search?q=email:a*&size=5000 a* stands
    for all email which starts with 'a', and it's the same with 'A' as email is
    case insensitive. The visitor will cover all cases from a to z, and yield
    the search URLs by passing each author in the release searching URL
    """

    def get_uris(self, content):
        release_visitor_template = 'https://fastapi.metacpan.org/release/_search?q=author:{id}&size=5000'
        hits = content.get('hits', {})
        inner_hits = hits.get('hits', [])
        for hit in inner_hits:
            _id = hit.get('_id')
            if not _id:
                continue
            yield URI(uri=release_visitor_template.format(id=_id), source_uri=self.uri)


@visit_router.route('https://fastapi.metacpan.org/release/_search\?q=author:\w+&size=5000')
class MetaCpanRleaseURLVisitors(HttpJsonVisitor):
    """
    Run the release results by searching the passing AUTHOR ID. The visitor will
    yield the json whose author ID is the passing author info. The
    implementation if the class is empty, it just returns for mapper use of the
    json content.
    """
    pass


@visit_router.route('http://www.cpan.org/modules/01modules.index.html')
class CpanModulesVisitors(HttpVisitor):
    """
    Return URIs by parsing  the HTML page of cpan modules page.
    """
    def get_uris(self, content):
        """
        Return the uris of authors pages, the returning URIs will be an input of
        CpanProjectHTMLVisitors
        """
        page = BeautifulSoup(content, 'lxml')
        url_template = 'http://www.cpan.org/{path}'
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue

            url = a['href']
            if not url:
                continue

            if url.startswith('../authors'):
                if url.endswith(('.zip', '.tar.gz')):
                    # Skip tar.gz since it will be captured by the CpanProjectHTMLVisitors
                    continue
                else:
                    url = url_template.format(path=url[3:])
                    yield URI(uri=url, source_uri=self.uri)


@visit_router.route('http://www.cpan.org/authors/.*/')
class CpanProjectHTMLVisitors(HttpVisitor):
    """
    Visit the HTML page of cpan project page and return the Packages info, HTML
    data and error.
    """
    def get_uris(self, content):
        """
        Return the uris by looking for the tar.gz in the html, and then forming
        the uri for meta and readme files
        """
        page = BeautifulSoup(content, 'lxml')
        if self.uri.endswith('/'):
            url_template = self.uri + '{path}'
        else:
            url_template = self.uri + '/{path}'
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue

            url = a['href']
            if not url:
                continue

            if url.startswith(('/', '?')):
                continue  # Avoid the directory and other non-file links
            else:
                name = url
                name = name.replace('tar.gz', ''). replace('.readme', '').replace('.meta', '')
                partions = name.rpartition('-')
                name = partions[0]
                version = partions[-1]
                package_url = None
                if name and version:
                    package_url = PackageURL(type='cpan', name=name, version=version).to_string()
                url = url_template.format(path=url)
                yield URI(uri=url, package_url=package_url, source_uri=self.uri)


@visit_router.route('http://www.cpan.org/.*.meta')
class CpanMetaVisitors(HttpVisitor):
    """
    Visit the meta file and return the meta data of the Package The goal
    of this visitor is to get the content instead of returning any valid
    uris.
    """
    pass


@visit_router.route('http://www.cpan.org/.*.readme')
class CpanReadmeVisitors(HttpVisitor):
    """
    Visit the readme file and translate to json and dump it and return for mapper use.
    """

    def dumps(self, content):
        """
        Return the json by parsing the readme content
        """
        # Handle bytes properly in python3
        if type(content) == bytes:
            content = content.decode('utf-8')

        lines = content.splitlines()
        readme_dict = dict()
        body = []
        head = None
        for line in lines:
            if len(line) > 1 and line.isupper() and line[0] != ' ':
                if head:
                    readme_dict[head] = '\n'.join(body).lstrip('\n').rstrip('\n')
                head = line
                body = []
            else:
                body.append(line.strip())
        return json.dumps(readme_dict)
