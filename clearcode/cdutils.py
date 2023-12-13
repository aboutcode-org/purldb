# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
#
# ClearCode is a free software tool from nexB Inc. and others.
# Visit https://github.com/nexB/clearcode-toolkit/ for support and download.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
from hashlib import md5
from itertools import zip_longest
import os
from os import path
import subprocess
import time
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from urllib.parse import parse_qs
from urllib.parse import quote_plus
from urllib.parse import unquote_plus

import attr
import click
from packageurl import PackageURL
import requests


"""
ClearlyDefined utlities.
"""

TRACE_FETCH = False
TRACE = False
TRACE_DEEP = False


PACKAGE_TYPES_BY_CD_TYPE = {
    'crate': 'cargo',
    'deb': 'deb',
    'debsrc': 'deb',
    # Currently used only for maven packages
    'sourcearchive': 'maven',
    'maven': 'maven',
    'composer': 'composer',
    # Currently used only for Github repo/packages
    'git': 'github',
    'pod': 'pod',
    'nuget': 'nuget',
    'pypi': 'pypi',
    'gem': 'gem',
    'npm': 'npm',
    'go': 'golang',
}


PACKAGE_TYPES_BY_PURL_TYPE = {
    'cargo': 'crate',
    'deb': 'deb',
    'maven': 'maven',
    'composer': 'composer',
    'github': 'git',
    'pod': 'pod',
    'nuget': 'nuget',
    'pypi': 'pypi',
    'gem': 'gem',
    'npm': 'npm',
}


PROVIDERS_BY_PURL_TYPE = {
    'cargo': 'cratesio',
    'deb': 'debian',
    'maven': 'mavencentral',
    'composer': 'packagist',
    # Currently used only for Github repo/packages
    'git': 'github',
    'github': 'github',
    'pod': 'cocoapods',
    'nuget': 'nuget',
    'pypi': 'pypi',
    'gem': 'rubygem',
    'npm': 'npmjs',
}


QUALIFIERS_BY_CD_TYPE = {
    'sourcearchive': {'classifier': 'sources'},
    'debsrc': {'arch': 'source'}
}


@attr.s(slots=True)
class Coordinate(object):
    """
    ClearlyDefined coordinates are used to identify any tracked component.
    """

    base_api_url = 'https://dev-api.clearlydefined.io'

    type = attr.ib()
    provider = attr.ib()
    namespace = attr.ib()
    name = attr.ib()
    revision = attr.ib()

    def __attrs_post_init__(self, *args, **kwargs):
        if self.provider == 'debian':
            self.namespace = 'debian'
        if not self.namespace:
            self.namespace = '-'

    @classmethod
    def from_dict(cls, coords):
        if 'namespace' not in coords:
            coords['namespace'] = '-'
        return cls(**coords)

    def to_dict(self):
        return attr.asdict(self)

    @classmethod
    def from_path(cls, pth, root=None):
        """
        Return a Coordinate from a path and an optional root.

        If a root is provided, the root is stripped from the path prefix.

        The remaining path is assumed to have its 5 leading segments mapping to
        the coordinate elements.

        For instance:

        >>> expected  = Coordinate('maven', 'mavencentral', 'io.dropwizard', 'dropwizard', '2.0.0-rc13')
        >>> p = '/maven/mavencentral/io.dropwizard/dropwizard/2.0.0-rc13/'
        >>> test = Coordinate.from_path(p)
        >>> assert expected == test

        >>> p = '/maven/mavencentral/io.dropwizard/dropwizard/2.0.0-rc13/scancode/3.2.2/'
        >>> test = Coordinate.from_path(p)
        >>> assert expected == test

        >>> u = 'https://api.clearlydefined.io/harvest/maven/mavencentral/io.dropwizard/dropwizard/2.0.0-rc13'
        >>> root = 'https://api.clearlydefined.io/harvest'
        >>> test = Coordinate.from_path(u, root)
        >>> assert expected == test

        >>> u = 'https://api.clearlydefined.io/harvest/maven/mavencentral/io.dropwizard/dropwizard/2.0.0-rc13/scancode/3.2.2'
        >>> root = 'https://api.clearlydefined.io/harvest'
        >>> test = Coordinate.from_path(u, root)
        >>> assert expected == test

        >>> p = '/maven/mavencentral/io.dropwizard/dropwizard/revision/2.0.0-rc13/tool/scancode/3.2.2.json'
        >>> test = Coordinate.from_path(p)
        >>> assert expected == test

        >>> p = '/maven/mavencentral/io.dropwizard/dropwizard/revision/2.0.0-rc13.json'
        >>> test = Coordinate.from_path(p)
        >>> assert expected == test

        """
        pth = pth.strip('/')
        if root and root in pth:
            root = root.strip('/')
            _, _, pth = pth.partition(root)

        segments = pth.strip('/').split('/')
        if len(segments) >= 6 and segments[4] == 'revision':
            # AZ blob style
            # /maven/mavencentral/io.dropwizard/dropwizard/revision/2.0.0-rc13.json
            # /maven/mavencentral/io.dropwizard/dropwizard/revision/2.0.0-rc13/tool/scancode/3.2.2.json
            start = segments[:4]
            version = segments[5]
            if version.endswith('.json'):
                version, _, _ = version.rpartition('.json')
            segments = start + [version]
        else:
            # plain API paths do not have a /revision/ segment
            segments = segments[:5]
        return cls(*segments)

    def to_api_path(self):
        return '{type}/{provider}/{namespace}/{name}/{revision}'.format(**self.to_dict())

    def to_def_blob_path(self):
        return '{type}/{provider}/{namespace}/{name}/revision/{revision}.json'.format(**self.to_dict())

    def to_harvest_blob_path(self, tool, tool_version):
        return '{type}/{provider}/{namespace}/{name}/revision/{revision}/tool/{tool}/{tool_version}.json'.format(
            tool=tool, tool_version=tool_version,
            **self.to_dict())

    def get_definition_api_url(self, base_api_url=None):
        """
        Return a URL to fetch the full definition.
        """
        return '{base_url}/definitions/{type}/{provider}/{namespace}/{name}/{revision}'.format(
            base_url=base_api_url or self.base_api_url,
            path=self.to_api_path(),
            **self.to_dict())

    def get_harvests_api_url(self, base_api_url=None):
        """
        Return a URL to fetch all harvests at once.
        """
        return '{base_url}/harvest/{type}/{provider}/{namespace}/{name}/{revision}?form=raw'.format(
            base_url=base_api_url or self.base_api_url,
            path=self.to_api_path(),
            **self.to_dict())

    def to_def_query_api_url(self, include_revision=False, base_api_url=None):
        """
        Return a CD API URL for query definitions.
        """
        qs = 'type={type}&provider={provider}&name{name}'
        if include_revision:
            qs += '&revision={revision}'
        if self.namespace and self.namespace != '-':
            qs += '&namespace={namespace}'
        qs = qs.format(
            base_url=base_api_url or self.base_api_url,
            **self.to_dict())
        return '{base_url}/definitions?{qs}'.format(**locals())

    def to_purl(self):
        """
        Return a PackageURL string containing this Coordinate's information

        >>> expected = 'pkg:maven/io.dropwizard/dropwizard@2.0.0-rc13'
        >>> test  = Coordinate('maven', 'mavencentral', 'io.dropwizard', 'dropwizard', '2.0.0-rc13').to_purl()
        >>> assert expected == str(test)

        >>> expected = 'pkg:maven/io.dropwizard/dropwizard@2.0.0-rc13?classifier=sources'
        >>> test  = Coordinate('sourcearchive', 'mavencentral', 'io.dropwizard', 'dropwizard', '2.0.0-rc13').to_purl()
        >>> assert expected == str(test)

        >>> expected = 'pkg:deb/debian/gedit-plugins@3.34.0-3?arch=source'
        >>> test  = Coordinate('debsrc', 'debian', '', 'gedit-plugins', '3.34.0-3').to_purl()
        >>> assert expected == str(test)
        """
        converted_package_type = PACKAGE_TYPES_BY_CD_TYPE[self.type]

        namespace = ''
        if self.namespace != '-':
            namespace = self.namespace

        if self.provider == 'debian':
            namespace = 'debian'

        qualifiers = {}
        if self.type in ('debsrc', 'sourcearchive',):
            qualifiers = QUALIFIERS_BY_CD_TYPE[self.type]

        return PackageURL(
            type=converted_package_type,
            namespace=namespace,
            name=self.name,
            version=self.revision,
            qualifiers=qualifiers,
        )

    @classmethod
    def from_purl(cls, purl):
        """
        Return a Coordinate containing the information from PackageURL `purl`

        >>> expected  = Coordinate('maven', 'mavencentral', 'io.dropwizard', 'dropwizard', '2.0.0-rc13')
        >>> purl = 'pkg:maven/io.dropwizard/dropwizard@2.0.0-rc13'
        >>> test = Coordinate.from_purl(purl)
        >>> assert expected == test

        >>> expected  = Coordinate('sourcearchive', 'mavencentral', 'io.dropwizard', 'dropwizard', '2.0.0-rc13')
        >>> purl = 'pkg:maven/io.dropwizard/dropwizard@2.0.0-rc13?classifier=sources'
        >>> test = Coordinate.from_purl(purl)
        >>> assert expected == test

        >>> expected  = Coordinate('debsrc', 'debian', '', 'gedit-plugins', '3.34.0-3')
        >>> purl = 'pkg:deb/debian/gedit-plugins@3.34.0-3?arch=source'
        >>> test = Coordinate.from_purl(purl)
        >>> assert expected == test
        """
        p = PackageURL.from_string(purl)

        package_type = p.type
        if package_type not in PACKAGE_TYPES_BY_PURL_TYPE:
            raise Exception('Package type is not supported by ClearlyDefined: {}'.format(package_type))
        # Handle the source types of Maven and Debian packages
        if package_type == 'maven' and p.qualifiers.get('classifier', '') == 'sources':
            package_type = 'sourcearchive'
            provider = 'mavencentral'
        elif package_type == 'deb' and p.qualifiers.get('arch', '') == 'source':
            package_type = 'debsrc'
            provider = 'debian'
        else:
            package_type = PACKAGE_TYPES_BY_PURL_TYPE[package_type]
            # TODO: Have way to set other providers?
            provider = PROVIDERS_BY_PURL_TYPE[package_type]

        return cls(
            type=package_type,
            provider=provider,
            namespace=p.namespace,
            name=p.name,
            revision=p.version,
        )


def get_coordinates(data_dir):
    """
    Yield tuple of (path, Coordinate) from definition directories from `data_dir`
    at full depth.
    """
    data_dir = data_dir.strip('/')
    for dirpath, dirnames, _filenames in os.walk(data_dir, followlinks=False):
        for d in dirnames:
            pth = path.join(dirpath, d)
            _, _, cdpth = pth.partition(data_dir)
            segments = cdpth.strip('/').split('/')
            # skip paths that have not the full depth required (e.g. 5 segments)
            if not len(segments) == 5:
                continue
            yield pth, Coordinate.from_path(cdpth)


def _get_response_content(url, retries=2, wait=2, session=requests, verbose=False, _retries=set()):
    """
    Return a tuple of (etag, md5, content bytes) with the content as bytes or as decoded
    text if `as_text` is True) of the response of a GET HTTP request at `url`.
    On HTTP errors (500 or higher), retry up to `retries` time after waiting
    `wait` seconds.
    """
    if verbose:
        click.echo('  --> Fetching: {url}'.format(**locals()))

    response = session.get(url, timeout=600)
    status_code = response.status_code

    if status_code == requests.codes.ok:  # NOQA
        # handle the case where the API returns an empty file and we need
        # to restart from an earlier continuation
        if url in _retries:
            _retries.remove(url)
            print(' SUCCESS after Failure to fetch:', url)
        etag = response.headers.get('etag')
        content = response.content
        checksum = md5(content).hexdigest()
        return etag, checksum, response.content

    error_code = requests.codes.get(status_code) or ''

    if status_code >= 500 and retries:
        # timeout/522 or other server error: let's wait a bit and retry for "retries" number of retries
        retries -= 1
        print(' Failure to fetch:', url, 'with', status_code, error_code, 'retrying after waiting:', wait, 'seconds.')
        _retries.add(url)
        time.sleep(wait)
        return _get_response_content(
            url=url, retries=retries, wait=wait, session=session, verbose=verbose)

    # all other errors
    raise Exception('Failed HTTP request for {url} : error: {status_code} : {error_code}'.format(**locals()))


def get_response_content(url, retries=2, wait=4, session=requests, verbose=False):
    """
    Return the bytes of the response of a GET HTTP request at `url`, an md5 checksum and the URL etag.
    On failures, retry up to `retries` time after waiting `wait` seconds.
    """
    try:
        return _get_response_content(
                url=url, retries=retries, wait=wait,
                session=session, verbose=verbose)
    except Exception as e:
        if retries:
            print(' Failure to fetch:', url, 'with error:', e, 'and retrying after waiting:', wait, 'seconds.')
            # we sleep progressively more after each failure and up to wait seconds
            time.sleep(int(wait / (retries or 1)))
            retries -= 1
            return get_response_content(
                url=url, retries=retries, wait=wait,
                session=session, verbose=verbose)
        else:
            raise


def split_url(url):
    """
    Given a URL, return a tuple of URL elements where `query` is a mapping.
    """
    scheme, netloc, path, query, fragment = urlsplit(url)
    query = parse_qs(query)
    return scheme, netloc, path, query, fragment


def join_qs(keys_values, do_not_quote=()):
    """
    Join a key/values mapping back into a query string.
    Quote values unless the name is in in the `do_not_quote` set.
    """
    keys_values = {
        k: (v[0] if v and isinstance(v, list) else v) for k, v in keys_values.items()}
    return '&'.join('='.join([k, v if k in do_not_quote else quote_plus(v)])
                    for k, v in keys_values.items())


def append_path_to_url(url, extra_path):
    """
    Return a new `url` with `extra_path` appended to its path.
    """
    scheme, netloc, path, query, fragment = split_url(url)
    path = path.strip('/') + '/' + extra_path.strip('/')
    segments = scheme, netloc, path, join_qs(query), fragment
    return urlunsplit(segments)


def update_url(url, qs_mapping, do_not_quote=()):
    """
    Return a new `url` with its query string updated from a mapping of key/value pairs.
    """
    scheme, netloc, path, query, fragment = split_url(url)
    query.update(qs_mapping)
    segments = scheme, netloc, path, join_qs(query, do_not_quote=do_not_quote), fragment
    return urlunsplit(segments)


def build_cdapi_continuation_url(api_url, continuation_token):
    """
    Return a new `api_url` with a CD API `continuation_token`.
    """
    return update_url(api_url, {'continuationToken': continuation_token})


def build_cdapi_continuation_url_from_coordinates(api_url, coordinates):
    """
    Return a new `api_url` with a continuation token built from
    a `coordinates` string. If a token is already present in the api_url it
    will be replaced.
    """
    continuation_token = get_cdapi_continuation_token(coordinates)
    return build_cdapi_continuation_url(api_url, continuation_token)


def split_cdapi_url(url):
    """
    Given a URL that may contain a continuation token, return a tuple of
    (cleaned url, token)
    """
    # get a continuation-free base URL. This assumes that the continuationToken
    # is always the last query string param if it is present.
    scheme, netloc, url, query, fragment = split_url(url)
    token = query.pop('continuationToken', None)
    if token:
        token = token[0]
        if '%' in token:
            token = unquote_plus(token)
    segments = scheme, netloc, url, join_qs(query), fragment
    unparsed = urlunsplit(segments)
    if TRACE:
        print('split_cdapi_url:', 'unparsed:', unparsed, 'token:', token)
    return unparsed, token


def get_coord_from_cdapi_continuation_url(api_url):
    """
    Given a URL that may contain a continuation token, return that as a decoded
    CD coordinate string or None.
    """
    # get a continuation-free base URL. This assumes that the continuationToken
    # is always the last query string param if it is present.
    _url, token = split_cdapi_url(api_url)
    if token:
        return get_coord_from_cdapi_continuation(token)


def get_coord_from_cdapi_continuation(continuation):
    """
    Given an encoded continuation token, return a string of CD coordinates.
    """
    if TRACE:
        print('get_coord_from_cdapi_continuation: continuation:', continuation)
    continuation = continuation.replace(' ', '+')

    if '%' in continuation:
        continuation = unquote_plus(continuation)

    decoded = base64.b64decode(continuation)
    if not isinstance(decoded, str):
        decoded = decoded.decode('utf-8')
    return decoded


def get_cdapi_continuation_token(coord):
    """
    Given a coord mapping or string of CD coordinates, return an encoded
    continuation token.
    """
    if isinstance(coord, dict):
        coord = coord2str(coord)
    coord = coord.replace(' ', '+')
    encoded = coord.encode('utf-8')

    return base64.b64encode(encoded).decode('utf-8')


def str2coord(s):
    """
    Return a mapping of CD coordinates from a `s` coordinates, URL or URN string.

    Some example of the supported input strings are:
        URL: "cd:/gem/rubygems/-/mocha/1.7.0"
        URN: "urn:gem:rubygems:-:mocha:revision:1.7.0:tool:scancode:3.1.0"
        plain: /gem/rubygems/foo/mocha/1.7.0"
    """
    #TODO: Add doctest
    is_urn = s.startswith('urn')
    is_url = s.startswith('cd:')
    splitter = ':' if is_urn else '/'
    segments = s.strip(splitter).split(splitter)
    if is_urn or is_url:
        segments = segments[1:]
    # ignore extra segments for now beyond the 5 fisrt (such as the PR of a curation)
    segments = segments[:5]

    fields = ('type', 'provider', 'namespace', 'name', 'revision',)
    return dict(zip_longest(fields, segments))


def coord2str(coord):
    """
    Return a path-like from a `coord` CD coordinates mapping.
    A non-present namespace is always represented as a dash (-)

    A mapping as these fields:
        "type": "git",
        "provider": "github",
        "namespace": "nexb",
        "name": "license-expression",
        "revision": "70277cdfc186466667cb58ec9f9c7281e68a221b"
    """
    assert coord, 'Empty or missing coordinate mapping: {}'.format(coord)
    rev = coord.get('revision')
    kwargs = dict(
        t=coord['type'],
        p=coord['provider'],
        ns=coord.get('namespace') or '-',
        n=coord['name'],
        r=rev,
    )
    if rev:
        template = '{t}/{p}/{ns}/{n}/{r}'
    else:
        template = '{t}/{p}/{ns}/{n}'
    return template.format(**kwargs)

