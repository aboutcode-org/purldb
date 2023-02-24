#
# Copyright (c) 2017 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import URI


class BowerSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://registry.bower.io/packages'


@visit_router.route('https://registry.bower.io/packages')
class BowerTopJsonVisitor(HttpJsonVisitor):
    """
    Collect URIs for all packages from the json returned.
    """

    def get_uris(self, content):
        """
        The json content is a list with name and url, like the following format:
        ...
          {
            "name": "bello",
            "url": "https://github.com/QiaoBuTang/bello.git"
          },
          {
            "name": "bello-gfw",
            "url": "https://gitcafe.com/GilbertSun/bello.git"
          },
        ...
        The url could be in the following formats like github, loglg, gitcafe, bitbuckets etc.
        # FIXME: We should cover all urls beyond the above four categories.
        """
        github_base_url = 'https://raw.githubusercontent.com/{owner}/{name}/master/bower.json'
        lolg_base_url = 'https://lolg.it/{owner}/{name}/raw/master/bower.json'
        gitcafe_base_url = 'https://coding.net/u/{owner}/p/{name}/git/raw/master/bower.json'
        bitbucket_base_url = 'https://bitbucket.org/{owner}/{name}/raw/master/bower.json'
        base_url_map = {
            'https://github.com/': github_base_url,
            'https://lolg.it/': lolg_base_url,
            'https://gitcafe.com/': gitcafe_base_url,
            'https://bitbucket.org/': bitbucket_base_url
        }
        for entry in content:
            name = entry.get('name')
            url = entry.get('url')
            if name in url:
                owner = None
                package_url = PackageURL(type='bower', name=name).to_string()
                for host_name, base_url in base_url_map.iteritems():
                    if url.startswith(host_name):
                        owner = url[len(host_name): url.index(name) - 1]
                        yield URI(uri=base_url.format(owner=owner, name=name), package_url=package_url, source_uri=self.uri)


@visit_router.route('https://raw.githubusercontent.com/.*/master/bower.json',
                    'https://lolg.it/.*/master/bower.json',
                    'https://coding.net/.*/master/bower.json',
                    'https://bitbucket.org/*/master/bower.json')
class BowerJsonVisitor(HttpJsonVisitor):
    """
    Collect content of the json itself by the visitor.
    """
    pass
