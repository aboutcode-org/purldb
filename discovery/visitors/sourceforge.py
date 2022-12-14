#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import re

from bs4 import BeautifulSoup

from packageurl import PackageURL

from discovery import seed
from discovery import visit_router
from discovery.visitors import HttpJsonVisitor
from discovery.visitors import HttpVisitor
from discovery.visitors import NonPersistentHttpVisitor
from discovery.visitors import URI


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class SourceforgeSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://sourceforge.net/sitemap.xml'


@visit_router.route('https?://sourceforge.net/sitemap.xml')
class SourceforgeSitemapIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect sub-sitemaps from the main sitemap. Return on URI for each sub-
    sitemap, for example: https://sourceforge.net/sitemap-167.xml

    Note that the class implements from NonPersistentHttpVisitor instead of HttpVisitor,
    as the XML file itself will be over 100M big, so NonPersistentHttpVisitor will be more
    reasonable.
    """

    def get_uris(self, content):
        """
        Collect all the sitemaps URIs from master sitemap.
        """
        locs = BeautifulSoup(open(content), 'lxml').find_all('loc')
        # Content passing from NonPersistentHttpVisitor is a temp file path
        # instead of file content, so opening to get a file handler is
        # necessary.
        for loc in locs:
            yield URI(uri=loc.text, source_uri=self.uri)


@visit_router.route('https?://sourceforge.net/sitemap-\d+.xml')
class SourceforgeSitemapPageVisitor(HttpVisitor):

    def get_uris(self, content):
        """
        Collect all the projects URIs from a sub-sitemaps.
        """
        sitemap_locs = BeautifulSoup(content, 'lxml').find_all('loc')
        regex = re.compile(
            r"^https?://sourceforge.net/projects/[a-z0-9.-]+/?$")
        for loc in sitemap_locs:
            if loc.text and re.match(regex, loc.text):
                project_json_baseurl = 'https://sourceforge.net/api/project/name/{}/json'
                project_name = loc.text.partition(
                    'https://sourceforge.net/projects/')[-1].strip('/')
                project_json_url = project_json_baseurl.format(project_name)
                package_url = PackageURL(type='sourceforge', name=project_name).to_string()
                # The priority in the xml has different view with the priority in visitor, so skip it.
                yield URI(uri=project_json_url, package_url=package_url, source_uri=self.uri)


@visit_router.route('https?://sourceforge.net/api/project/name/[a-z0-9.-]+/json',
                    'https?://sourceforge.net/rest/p/[a-z0-9.-]+'
                    )
class SourceforgeProjectJsonVisitor(HttpJsonVisitor):
    """
    Collect Sourceforge project data through the JSON API.
    The implementation is empty since it will inherit the implementation from HttpJsonVisitor and it returns json data for mapper.
    """
    pass
