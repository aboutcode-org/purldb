#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from packageurl import PackageURL

from minecode import seed
from minecode.utils import get_http_response
from minecode import visit_router

from minecode.visitors import HttpJsonVisitor
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class GitlabSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://gitlab.com/api/v4/projects'


@visit_router.route('https://gitlab.com/api/v4/projects')
class GitlabAPIHeaderVisitor(HttpVisitor):
    """
    Get the header of the API, and parse the page size and total pages from the
    header, and yield urls for further visiting like GitlabAPIVisitor
    """

    def fetch(self, uri, timeout=10):
        """
        Return only the headers of the response.
        """
        return get_http_response(uri, timeout).headers

    def get_uris(self, content):
        new_page_template = 'https://gitlab.com/api/v4/projects?page={next_page}&per_page={per_page}&statistics=true'

        page_size = content.get('X-Per-Page')
        total_pages = content.get('X-Total-Pages')
        if page_size and total_pages:
            total_pages = int(total_pages)
            for i in range(total_pages):
                # Use the loop  to yield the uri of next page of the visitor.
                nextpage_url = new_page_template.format(next_page=i + 1, per_page=page_size)
                yield URI(uri=nextpage_url, source_uri=self.uri, visited=False)


@visit_router.route('https://gitlab.com/api/v4/projects\?page=\d+&per_page=\d+&statistics=true')
class GitlabAPIVisitor(HttpJsonVisitor):
    """
    Return URIs from the json content of one API page returned from gitlab api.
    This yields the "web_url" from each package in the current json page.
    """

    def get_uris(self, content):
        """Yield URIs from the json content, the passing content is the json info, the example is:
        [
              {
                "id": 6377679,
                ...
                "web_url": "https://gitlab.com/prithajnath/cnn-keras",
                ...
              },
              {
                ..
                  "web_url": "https://gitlab.com/janpoboril/rules-bug",
                ...
             }
            ...
            ]
        Each element in the list is a dictionary, and we concern the web_url for the visitor and also return the data.
        """

        if not content:
            # If the page is empty, just return
            return
        for element in content:
            # The element is one package in the list of current returned page.
            url = element.get('web_url')
            if url:
                project_name = url.rpartition('/')[-1]
                package_url = PackageURL(type='gitlab', name=project_name).to_string()
                yield URI(uri=url, package_url=package_url, data=element, source_uri=self.uri, visited=False)
