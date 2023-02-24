#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from bs4 import BeautifulSoup

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class FreedesktopSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://www.freedesktop.org/wiki/Software'


@visit_router.route('https://www.freedesktop.org/wiki/Software')
class FreedesktopHTMLVisitor(HttpVisitor):
    """
    Visit the Freedesktop Software HTML page and return URIs parsed from HTML page.
    """
    def get_uris(self, content):
        url_template = 'https://www.freedesktop.org/wiki/Software/{name}'
        page = BeautifulSoup(content, 'lxml')
        for div in page.find_all(name='div'):
            for a in div.find_all(name='a'):
                if 'href' not in a.attrs:
                    continue
                href = a['href']
                if href and href.startswith('./'):
                    project_name = href.replace('./', '').strip('/')
                    package_url = PackageURL(type='freedesktop', name=project_name).to_string()
                    yield URI(uri=url_template.format(name=project_name), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://www.freedesktop.org/wiki/Software/.*')
class FreedesktopProjectHTMLVisitor(HttpVisitor):
    """
    Visit the Freedesktop Project HTML page.
    """
    pass
