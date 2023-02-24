#
# Copyright (c) 2017 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals


from bs4 import BeautifulSoup

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class CranSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://cloud.r-project.org/web/packages/available_packages_by_date.html'


@visit_router.route('https://cloud.r-project.org/web/packages/available_packages_by_date.html')
class CranPackagesVisitors(HttpVisitor):
    """
    Return URIs by parsing the HTML content of the page
    """
    def get_uris(self, content):
        base_url = 'https://cloud.r-project.org/web/packages/{package}/index.html'
        a_blocks = BeautifulSoup(content, 'lxml').find_all('a')
        for a in a_blocks:
            package = a.text
            package_url = PackageURL(type='cran', name=package).to_string()
            yield URI(uri=base_url.format(package=package), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://cloud.r-project.org/web/packages/[\w\-\.]/index.html')
class CranSinglePackageVisitor(HttpVisitor):
    """
    Return only the HTML content of the page, and will be parsed in mapper
    """
    pass
