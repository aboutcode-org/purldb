# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import URI


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


"""
Mercurial support is retiring in mid 2020 and only git is
available after that.
https://bitbucket.org/blog/sunsetting-mercurial-support-in-bitbucket


TODO: collect actual packages....
TODO: collect counts and more:
watchers count:
    https://api.bitbucket.org/2.0/repositories/mikael/stellaris/watchers?fields=size
forks count:
    https://api.bitbucket.org/2.0/repositories/mikael/stellaris/forks?fields=size
tags:
    https://api.bitbucket.org/2.0/repositories/mchaput/whoosh/refs/tags
then the tag download is with:
   https://bitbucket.org/pypa/setuptools/get/<tag>.zip
   https://bitbucket.org/pypa/setuptools/get/20.1.1.tar.bz2

the latest commit to get a download link:
    https://api.bitbucket.org/2.0/repositories/pypa/setuptools/commits
    This gets the count of commits.
    the link is then: https://bitbucket.org/pypa/setuptools/get/<commit>.tar.bz2

the downloads if any:
https://api.bitbucket.org/2.0/repositories/pypa/setuptools/downloads
each download has a count and a URL such as:
https://api.bitbucket.org/2.0/repositories/pypa/setuptools/downloads/setuptools-19.6b1.zip
 this URL can also be built using the filename as:
 https://bitbucket.org/pypa/setuptools/downloads/setuptools-19.6b1.zip

Also there is no value to add repos that are empty and have no downloads.
Therefore we should better:
1. collect repo data as a "template" only record
2. effectively create package IFF there are commits and/or downloads.
2.1 if commits and no tags: make a single package using the latest commit
2.2 if tags: use these for packages
2.3 if downloads: use these packages

NB: we can also get only certain fields:
https://api.bitbucket.org/2.0/repositories/pypa/setuptools?pagelen=1&fields=size,links,full_name
https://api.bitbucket.org/2.0/repositories/pypa/setuptools/watchers?pagelen=1&fields=size,values.links
"""


class BitbucketSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://api.bitbucket.org/2.0/repositories?pagelen=400'


# TODO: review mapper
@visit_router.route('https://api\.bitbucket\.org/2\.0/repositories\?pagelen=.*',)
class BitbucketIndexVisitor(HttpJsonVisitor):
    """
    Collect repository data through paginated API calls.
    The index contains repo-level data for every repo.
    """
    def get_uris(self, content):
        next_page = content.get('next')
        if next_page:
            yield URI(uri=next_page, source_uri=self.uri)


@visit_router.route('https://api\.bitbucket\.org/2\.0/repositories/[^\/]*/[^\/\?]*/?')
class BitbucketSingleRepoVisitor(HttpJsonVisitor):
    """
    Collect data for a single repository.
    Note: this is strictly equivalent to one item of the index paginated calls.
    """
    def get_uris(self, content):
        return get_repo_uris(content, source_uri=self.uri)


@visit_router.route('https://api.bitbucket.org/2.0/repositories/[^\/]*/[^\/]*/(refs/tags|downloads).*')
class BitbucketDetailsVisitorPaginated(HttpJsonVisitor):
    """
    Collect repository details for data that are paginated.
    """
    def get_uris(self, content):
        next_page = content.get('next')
        if next_page:
            purl = get_purl(self.uri)
            yield URI(uri=next_page, source_uri=self.uri, package_url=purl)


@visit_router.route(
    'https://api\.bitbucket\.org/2\.0/repositories/[^\/]*/[^\/]*/(watchers|forks|commits).*')
class BitbucketDetailsVisitor(HttpJsonVisitor):
    """
    Collect repository details for data that are not paginated.
    """
    pass


def get_repo_ns_name(url_like):
    """
    Return a namespace and name for a bitbucket repo given something that looks
    like a bitbucket URL.

    For example:
    >>> get_repo_ns_name('https://api.bitbucket.org/2.0/repositories/bastiand/mercurialeclipse/refs/tags?pagelen=2')
    ('bastiand', 'mercurialeclipse')
    >>> get_repo_ns_name('https://bitbucket.org/bastiand/mercurialeclipse/src')
    ('bastiand', 'mercurialeclipse')
    >>> get_repo_ns_name('/bastiand/mercurialeclipse/src')
    ('bastiand', 'mercurialeclipse')
    """
    if url_like.startswith('https://api.bitbucket.org'):
        head, _, path = url_like.partition('2.0/repositories')
        if head:
            segments = [p for p in path.split('/') if p]
            if len(segments) >= 2:
                ns = segments[0]
                name = segments[1]
                return ns, name

    if url_like.startswith('https://bitbucket.org/'):
        head, _, path = url_like.partition('bitbucket.org/')
        if head:
            segments = [p for p in path.split('/') if p]
            if len(segments) >= 2:
                ns = segments[0]
                name = segments[1]
                return ns, name

    segments = [p for p in url_like.strip('/').split('/') if p]
    if len(segments) >= 2:
        ns = segments[0]
        name = segments[1]
        return ns, name


def get_purl(url_like):
    """
    Return a Package URL string created from a bitbucket url or url-like.
    """
    ns_name = get_repo_ns_name(url_like)
    if not ns_name:
        return
    ns, name = ns_name
    return PackageURL(type='bitbucket', namespace=ns, name=name).to_string()


def get_repo_uris(repo_data, source_uri):
    """
    Yield URIs from a single repository `repo_data` data.
    """
    full_name = repo_data.get('full_name', '').strip()
    package_url = get_purl(full_name)
    links = repo_data.get('links', {})
    repo_uri = links.get('html', {}).get('href')
    if not repo_uri:
        repo_uri = 'https://bitbucket.org/{full_name}'.format(full_name=full_name)

    # Yield URI for latest commits, tags and downloads as candidate packages.
    commits_url = links.get('commits', {}).get('href')
    # we only care about the latest commit
    commits_url += '?pagelen=1'
    yield URI(uri=commits_url, package_url=package_url, source_uri=source_uri)

    # for counts only: these should go to the package template
    for link in ('forks', 'watchers'):
        url = links.get(link, {}).get('href')
        if url:
            # we get a single fields and only one page
            url += '?pagelen=1&fields=size'
            yield URI(uri=url, package_url=package_url, source_uri=source_uri)

    for link in ('refs/tags', 'downloads'):
        url = links.get(link, {}).get('href')
        if url:
            # paginated, we want them all
            url += '?pagelen=100'
            yield URI(uri=url, package_url=package_url, source_uri=source_uri)
