#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import json

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router

from minecode.visitors import NonPersistentHttpVisitor
from minecode.visitors import URI


class GoLangSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://api.godoc.org/packages'


@visit_router.route('https://api.godoc.org/packages')
class GodocIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect Golang URIs for packages available in the Go doc index.
    """

    def get_uris(self, content):
        """
        Return URIs to search the API further for a package
        """
        seen_paths = set()
        for path, package in get_packages(content):
            package_url, path = parse_package_path(path)
            if path in seen_paths:
                continue
            seen_paths.add(path)

            # note the addition of a * at the end of the search string...
            # without this the returned data are sparse
            details_url = 'https://api.godoc.org/search?q={path}*'.format(**locals())
            host = get_well_known_host(path)
            # If the path belongs github/bitbucket, yield a repo too
            if host:
                # keep github, bitbucket... as type:
                repo_type, _, _ = host.lower().partition('.')  # NOQA
                repo_url = 'https://{namespace}/{name}'.format(**package_url.to_dict())
                repo_purl = PackageURL(
                    type=repo_type,
                    namespace=package_url.namespace,
                    name=package_url.name,
                    qualifiers=dict(package_url=package_url.to_string())
                ).to_string()

                yield URI(uri=repo_url, package_url=repo_purl, source_uri=self.uri)

                yield URI(uri=details_url,
                          package_url=package_url.to_string(),
                          source_uri=self.uri)

            else:
                yield URI(uri=details_url, package_url=package_url, source_uri=self.uri)


@visit_router.route('https://api\.godoc\.org/search\?q=.*')
class GodocSearchVisitor(NonPersistentHttpVisitor):
    """
    Collect URIs and data through the godoc searchi API.
    """

    def get_uris(self, content):
        seen_paths = set()
        for path, package in get_packages(content):
            package_url, path = parse_package_path(path)
            if path in seen_paths:
                continue
            seen_paths.add(path)

            purl = package_url.to_string()
            yield URI(
                # NOTE: here we use a previsited PURL as URI
                uri=purl,
                package_url=purl,
                source_uri=self.uri,
                # the data contains some popcounts and a description
                data=package,
                visited=True)


def get_packages(packages_json_location):
    """
    Yield a path and mapping of Go package raw data from a JSON data location.
    {
      "name": "aws",
      "path": "github.com/aws/aws-sdk-go/aws",
      "import_count": 13623,
      "synopsis": "Package aws provides the core SDK's utilities and shared types.",
      "stars": 4218,
      "score": 0.99
    },
    """
    with open(packages_json_location) as f:
        data = json.load(f)
    for package in data.get('results', []):
        path = package['path']
        if path and not is_standard_import(path):
            yield path, package


def is_standard_import(path):
    """
    Return True if a Go import path is for a standard library import
    """
    standard_packages = (
        'archive',
        'bufio',
        'builtin',
        'bytes',
        'compress',
        'container',
        'context',
        'crypto',
        'database',
        'debug',
        'encoding',
        'expvar',
        'flag',
        'fmt',
        'go',
        'hash',
        'html',
        'image',
        'index',
        'io',
        'log',
        'math',
        'mime',
        'net',
        'os',
        'path',
        'plugin',
        'reflect',
        'regexp',
        'runtime',
        'sort',
        'strconv',
        'strings',
        'sync',
        'syscall',
        'testing',
        'text',
        'time',
        'unsafe',
        'golang.org/x/benchmarks',
        'golang.org/x/blog',
        'golang.org/x/build',
        'golang.org/x/crypto',
        'golang.org/x/debug',
        'golang.org/x/image',
        'golang.org/x/mobile',
        'golang.org/x/net',
        'golang.org/x/perf',
        'golang.org/x/review',
        'golang.org/x/sync',
        'golang.org/x/sys',
        'golang.org/x/text',
        'golang.org/x/time',
        'golang.org/x/tools',
        'golang.org/x/tour',
        'golang.org/x/exp'
    )

    return path.startswith(standard_packages)


repo_hosters = 'bitbucket.org/', 'github.com/', 'gitlab.com/'


def get_well_known_host(path):
    """
    Return a host if this path is from a well known hoster or None.
    """
    if path.startswith(repo_hosters):
        host, _, _ = path.partition('.')
        return host


def parse_package_path(path):
    """
    Return a PackageURL and transformed path given a path to a Go import.
    """
    path = path or ''
    segments = path.split('/')

    host = get_well_known_host(path)
    qualifiers = None
    if host:
        # keep only the first few segments
        segments = segments[:3]
        repo_url = 'https://' + '/'.join(segments)
        qualifiers = dict(vcs_repository=repo_url)
    namespace = None
    if len(segments) > 1:
        namespace = segments[:-1]
        namespace = '/'.join(namespace)

    name = segments[-1]

    path = '/'.join(segments)

    package_url = PackageURL(
        type='golang',
        namespace=namespace,
        name=name,
        qualifiers=qualifiers
    )

    return package_url, path
