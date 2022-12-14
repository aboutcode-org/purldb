#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import os

from bs4 import BeautifulSoup

from discovery import seed
from discovery import visit_router
from discovery.utils import extract_file
from discovery.visitors import HttpVisitor
from discovery.visitors import NonPersistentHttpVisitor
from discovery.visitors import URI

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class FreeBSDSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://pkg.freebsd.org'


@visit_router.route('https://pkg.freebsd.org')
class FreeBSDBaseHTMLVisitors(HttpVisitor):
    """
    Visit the freeBSD home link and yield uri for each FreeBSD repo
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        base_url = 'https://pkg.freebsd.org/{path}/'
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs:
                continue
            href = a['href']
            # the sub link useful is like: FreeBSD:13:aarch64
            if href and href.startswith('FreeBSD%3A'):
                url = base_url.format(path=href)
                yield URI(uri=url, source_uri=self.uri)


@visit_router.route('https://pkg.freebsd.org/.*/')
class FreeBSDSubHTMLVisitors(HttpVisitor):
    """
    Visit the sub repo URL and yield all uris in the page and in its children page
    """
    def get_uris(self, content):
        page = BeautifulSoup(content, 'lxml')
        base_url = self.uri + '{path}'
        for a in page.find_all(name='a'):
            if 'href' not in a.attrs or 'title' not in a.attrs:
                # parent link doesn't have title.
                continue
            href = a['href']
            url = base_url.format(path=href)
            yield URI(uri=url, source_uri=self.uri)


@visit_router.route('https://pkg.freebsd.org/.*packagesite.txz')
class FreeBSDIndexVisitors(NonPersistentHttpVisitor):
    """
    Extract packagesite.txz index file, get the data of packagesite.yaml file.
    """
    def dumps(self, content):
        """
        Extract the file packagesite.yaml and read the content of the file and return.
        """
        extracted_location = extract_file(content)
        manifest_file = os.path.join(extracted_location, 'packagesite.yaml')
        if os.path.exists(manifest_file):
            with open(manifest_file) as file_handler:
                return file_handler.read()
        else:
            logger.warn('The packagesite.yaml is not existing in index file:' + content)
