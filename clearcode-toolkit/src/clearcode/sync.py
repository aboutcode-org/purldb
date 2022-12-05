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

from datetime import datetime
import gzip
import json
from multiprocessing import pool
import os
from os import path
import time

import click
from django.utils import timezone
import requests

from clearcode import cdutils


"""
Fetch the latest definitions and harvests from ClearlyDefined

Theory of operation
-------------------

We can access on a regular basis a limited subset of the most recently updated
definitions, by batches of 100 definitions using this query:
    https://api.clearlydefined.io/definitions?matchCasing=false&sort=releaseDate&sortDesc=true

We can also focus this on a type as in:
    https://api.clearlydefined.io/definitions?matchCasing=false&sort=releaseDate&sortDesc=true&type=git

This provides incomplete definitions (they do not contain files).

From there we can fetch:
 - each definition (or possibly many as a batch at once)
 - each harvest either by batching all harvest tools at once or fetching them
   one by one.
 - any referenced attachment

Since the definition batches are roughly stopping after 2000 when sorted by
latest date, we can repeat this every few minutes or so forever to catch any
update. We use etags and a cache to avoid refetching things that have not
changed.
"""

TRACE = False


# TODO: update when this is updated upstream
# https://github.com/clearlydefined/service/blob/master/schemas/definition-1.0.json#L17
known_types = (
    # fake empty type
    None,
    'npm',
    'git',
    'pypi',
    'composer',
    'maven',
    'gem',
    'nuget',
    'sourcearchive',
    'deb',
    'debsrc',
    'crate',
    'pod',
)


# each process gets its own session
session = requests.Session()


def fetch_and_save_latest_definitions(
        base_api_url, cache, output_dir=None, save_to_db=False,
        by_latest=True, retries=2, verbose=True):
    """
    Fetch ClearlyDefined definitions and paginate through. Save these as blobs
    to data_dir.

    Fetch the most recently updated definitions first if `by_latest` is True.
    Otherwise, the order is not specified.
    NOTE: these do not contain file details (but the harvest do)
    """
    assert output_dir or save_to_db, 'You must select one of the --output-dir or --save-to-db options.'

    if save_to_db:
        from clearcode import dbconf
        dbconf.configure(verbose=verbose)

    definitions_url = cdutils.append_path_to_url(base_api_url, extra_path='definitions')
    if by_latest:
        definitions_url = cdutils.update_url(definitions_url, qs_mapping=dict(sort='releaseDate', sortDesc='true'))

    for content in fetch_definitions(api_url=definitions_url, cache=cache, retries=retries, verbose=TRACE):
        # content is a batch of 100 definitions
        definitions = content and content.get('data')
        if not definitions:
            if verbose:
                print('  No more data for: {}'.format(definitions_url))
            break

        if verbose:
            first = cdutils.coord2str(definitions[0]['coordinates'])
            last = cdutils.coord2str(definitions[-1]['coordinates'])
            print('Fetched definitions from :', first, 'to:', last, flush=True)
        else:
            print('.', end='', flush=True)

        savers = []
        if save_to_db:
            savers.append(db_saver)
        if output_dir:
            savers.append(file_saver)

        # we received a batch of definitions: let's save each as a Gzipped JSON
        for definition in definitions:
            coordinate = cdutils.Coordinate.from_dict(definition['coordinates'])
            for saver in savers:
                blob_path, _size = save_def(
                    coordinate=coordinate, content=definition, output_dir=output_dir,
                    saver=saver)
            yield coordinate, blob_path


def fetch_definitions(api_url, cache, retries=1, verbose=True):
    """
    Yield batches of definitions each as a list of mappings from calling the
    ClearlyDefined API at `api_url`. Retry on failure up to `retries` times.
    Raise an exception on failure. Raise an EmptyReponse on success but empty
    response (a CD API quirk).

    Paginate using the API's `continuationToken`. If provided as a start, this
    token should be in the initial URL query string.

    The structure of the REST payload is a list :
        {"data": [{}, ...], "continuationToken": ""}
    """
    assert '/definitions' in api_url
    content = None
    errors_count = 0
    max_errors = 5
    while True:
        try:
            content = cache.get_content(api_url, retries=retries, session=session)
            if not content:
                break
            content = json.loads(content)

        except requests.exceptions.ConnectionError as ex:
            print('!!!!!!!!!!!!!!!!!! -> Request failed, retrying:', api_url, 'with:', ex)
            errors_count += 1
            if errors_count <= max_errors:
                # wait and retry, sleeping more each time we egt some error
                time.sleep(errors_count * 3)
                continue
            else:
                raise

        continuation_token = ''
        if content:
            yield content
            continuation_token = content.get('continuationToken', '')

        if not continuation_token:
            if verbose:
                print('  No more data for: {}'.format(api_url))
            break

        api_url = cdutils.build_cdapi_continuation_url(api_url, continuation_token)


def compress(content):
    """
    Return a byte string of `content` gzipped-compressed.
    `content` is eiher a string or a JSON-serializable data structure.
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    else:
        content = json.dumps(content , separators=(',', ':')).encode('utf-8')
    return gzip.compress(content, compresslevel=9)


def file_saver(content, blob_path, output_dir, **kwargs):
    """
    Save `content` bytes (or dict or string) as gzip compressed bytes to `file_path`.
    Return the length of the written payload or 0 if it existed and was not updated.
    """
    file_path = path.join(output_dir, blob_path + '.gz')
    compressed = compress(content)

    if path.exists(file_path):
        with open(file_path , 'rb') as ef:
            existing = ef.read()
            if existing == compressed:
                return 0
    else:
        parent_dir = path.dirname(file_path)
        os.makedirs(parent_dir, exist_ok=True)

    with open(file_path , 'wb') as oi:
        if TRACE:
            print('Saving:', blob_path)
        oi.write(compressed)
    return len(compressed)


def db_saver(content, blob_path, **kwargs):
    """
    Save `content` bytes (or dict or string) identified by `file_path` to the
    configured DB. Return the length of the written payload or 0 if it existed
    and was not update.
    """
    from clearcode import models

    compressed = compress(content)

    cditem, created = models.CDitem.objects.get_or_create(path=blob_path)
    if not created:
        if cditem.content != compressed and cditem.last_modified_date < timezone.now():
            cditem.content = compressed
            cditem.save()
            if TRACE:
                print('Updating content for:', blob_path)
        else:
            return 0
    else:
        if TRACE:
            print('Adding content for:', blob_path)

    return len(compressed)


def save_def(coordinate, content, output_dir, saver=file_saver):
    """
    Save the definition `content` bytes (or dict or string) for `coordinate`
    object to `output_dir` using blob paths conventions.

    Return a tuple of the ( saved file path, length of the written payload).
    """
    blob_path = coordinate.to_def_blob_path()
    return blob_path, saver(content=content, output_dir=output_dir, blob_path=blob_path)


def save_harvest(
        coordinate, tool, tool_version, content, output_dir, saver=file_saver):
    """
    Save the scan `content` bytes (or dict or string) for `tool` `tool_version`
    of `coordinate` object to `output_dir` using blob paths conventions.

    Return a tuple of the ( saved file path, length of the written payload).
    """
    blob_path = coordinate.to_harvest_blob_path(tool, tool_version)
    return blob_path, saver(content=content, output_dir=output_dir, blob_path=blob_path)


def fetch_and_save_harvests(
        coordinate, cache, output_dir=None, save_to_db=False, retries=2,
        session=session, verbose=True):
    """
    Fetch all the harvests for `coordinate` Coordinate object and save them in
    `outputdir` using blob-style paths, one file for each harvest/scan.

    (Note: Return a tuple of (etag, md5, url) for usage as a callback)
    """
    assert output_dir or save_to_db, 'You must select one of the --output-dir or --save-to-db options.'
    if save_to_db:
        from clearcode import dbconf
        dbconf.configure(verbose=verbose)

    url = coordinate.get_harvests_api_url()
    etag, checksum, content = cache.get_content(
        url, retries=retries, session=session, with_cache_keys=True)

    if content:
        savers = []
        if save_to_db:
            savers.append(db_saver)
        if output_dir:
            savers.append(file_saver)

        if verbose:
            print('  Fetched harvest for:', coordinate.to_api_path(), flush=True)
        else:
            print('.', end='', flush=True)

        for tool, versions in json.loads(content).items():
            for tool_version, harvest in versions.items():
                for saver in savers:
                    save_harvest(
                        coordinate=coordinate,
                        tool=tool,
                        tool_version=tool_version,
                        content=harvest,
                        output_dir=output_dir,
                        saver=saver)

    return etag, checksum, url


class Cache(object):
    """
    A caching object for etags and checksums to avoid refetching things.
    """

    def __init__(self, max_size=100 * 1000):
        self.etags_cache = {}
        self.checksums_cache = {}
        self.max_size = max_size

    def is_unchanged_remotely(self, url, session=session):
        """
        Return True if a `url` content is unchanged from cache based on HTTP
        HEADER Etag.
        """
        try:
            response = session.head(url)
            remote_etag = response.headers.get('etag')
            if remote_etag and self.etags_cache.get(url) == remote_etag:
                return True
        except:
            return False

    def is_fetched(self, checksum, url):
        """
        Return True if the content checksum exists for url, using MD5 checksum.
        """
        return url and checksum and self.checksums_cache.get(checksum) == url

    def add(self, etag, checksum, url):
        if etag:
            self.etags_cache[url] = etag
        if checksum:
            self.checksums_cache[checksum] = url

    def add_args(self, args):
        self.add(*args)

    def trim(self):
        """
        Trim the cache to its max size.
        """

        def _resize(cache):
            extra_items = len(cache) - self.max_size
            if extra_items > 0:
                for ei in list(cache)[:extra_items]:
                    del cache[ei]

        _resize(self.etags_cache)
        _resize(self.checksums_cache)

    def get_content(self, url, retries=1, session=session, with_cache_keys=False):
        """
        Return fetched content as bytes or None if already fetched or unchanged.
        Updates the cache as needed.
        """
        if self.is_unchanged_remotely(url=url, session=session):
            return

        etag, checksum, content = cdutils.get_response_content(
            url, retries=retries, session=session)

        if not content:
            return

        if self.is_fetched(checksum, url):
            return

        self.add(etag, checksum, url)

        if with_cache_keys:
            return etag, checksum, content
        else:
            return content

    def copy(self):
        """
        Return a deep copy of self
        """
        cache = Cache(self.max_size)
        cache.checksums_cache = dict(self.checksums_cache)
        cache.etags_cache = dict(self.etags_cache)
        return cache


@click.command()

@click.option('--output-dir',
    type=click.Path(), metavar='DIR',
    help='Save fetched content as compressed gzipped files to this output directory.')

@click.option('--save-to-db',
    is_flag=True,
    help='Save fetched content as compressed gzipped blobs in the configured database.')

@click.option('--unsorted',
    is_flag=True,
    help='Fetch data without any sorting. The default is to fetch data sorting by latest updated first.')

@click.option('--base-api-url',
    type=str,
    default='https://api.clearlydefined.io', show_default=True,
    help='ClearlyDefined base API URL.')

@click.option('--wait',
    type=int, metavar='INT',
    default=60, show_default=True,
    help='Set the number of seconds to wait for new or updated definitions '
         'between two loops.')

@click.option('-n', '--processes',
    type=int, metavar='INT',
    default=1, show_default=True,
    help='Set the number of parallel processes to use. '
         'Disable parallel processing if 0.')

@click.option('--max-def',
    type=int, metavar='INT',
    default=0,
    help='Set the maximum number of definitions to fetch.')

@click.option('--only-definitions',
    is_flag=True,
    help='Only fetch definitions and no other data item.')

@click.option('--log-file',
    type=click.Path(), default=None,
    help='Path to a file where to log fetched paths, one per line. '
         'Log entries will be appended to this file if it exists.')

@click.option('--verbose',
    is_flag=True,
    help='Display more verbose progress messages.')

@click.help_option('-h', '--help')
def cli(output_dir=None, save_to_db=False,
        base_api_url='https://api.clearlydefined.io',
        wait=60, processes=1, unsorted=False,
        log_file=None, max_def=0, only_definitions=False, session=session,
        verbose=False, *arg, **kwargs):
    """
    Fetch the latest definitions and harvests from ClearlyDefined and save these
    as gzipped JSON either as as files in output-dir or in a PostgreSQL
    database. Loop forever after waiting some seconds between each cycles.
    """
    assert output_dir or save_to_db, 'You must select at least one of the --output-dir or --save-to-db options.'

    fetch_harvests = not only_definitions

    cycles = 0
    total_defs_count = 0
    total_duration = 0

    coordinate = None
    file_path = None

    cache = Cache(max_size=100 * 1000)

    sleeping = False
    harvest_fetchers = None

    log_file_fn = None
    if log_file:
        log_file_fn = open(log_file, 'a')

    try:
        if fetch_harvests:
            harvest_fetchers = pool.Pool(processes=processes, maxtasksperchild=10000)

        # loop forever. Complete one loop once we have fetched all the latest
        # items and we are not getting new pages (based on etag)
        # Sleep between each loop
        while True:
            start = time.time()
            cycles += 1
            cycle_defs_count = 0

            # iterate all types to get more depth for the latest defs.
            for def_type in known_types:
                sleeping = False

                if def_type:
                    # get latest with a "type" query
                    def_api_url = cdutils.update_url(base_api_url, qs_mapping=dict(type=def_type))
                else:
                    # do nothing if we have no type
                    def_api_url = base_api_url

                definitions = fetch_and_save_latest_definitions(
                    base_api_url=def_api_url,
                    output_dir=output_dir,
                    save_to_db=save_to_db,
                    cache=cache,
                    by_latest=not unsorted,
                    verbose=verbose)

                for coordinate, file_path in definitions:

                    cycle_defs_count += 1

                    if log_file:
                        log_file_fn.write(file_path.partition('.gz')[0] + '\n')

                    if TRACE: print('  Saved def for:', coordinate)

                    if fetch_harvests:
                        kwds = dict(
                            coordinate=coordinate,
                            output_dir=output_dir,
                            save_to_db=save_to_db,
                            # that's a copy of the cache, since we are in some
                            # subprocess, the data is best not shared to avoid
                            # any sync issue
                            cache=cache.copy(),
                            verbose=verbose)

                        harvest_fetchers.apply_async(
                            fetch_and_save_harvests,
                            kwds=kwds,
                            callback=cache.add_args)

                    if max_def and max_def <= cycle_defs_count:
                        break

                if max_def and (max_def <= cycle_defs_count or max_def <= total_defs_count):
                    break

            total_defs_count += cycle_defs_count
            cycle_duration = time.time() - start
            total_duration += cycle_duration

            if not sleeping:
                print('Saved', cycle_defs_count, 'defs and harvests,',
                      'in:', int(cycle_duration), 'sec.')

                print('TOTAL cycles:', cycles,
                      'with:', total_defs_count, 'defs and combined harvests,',
                      'in:', int(total_duration), 'sec.')

                print('Cycle completed at:', datetime.utcnow().isoformat(),
                      'Sleeping for', wait, 'seconds...')
            else:
                print('.', end='')

            sleeping = True
            time.sleep(wait)
            cache.trim()

    except KeyboardInterrupt:
        click.secho('\nAborted with Ctrl+C!', fg='red', err=True)
        return

    finally:
        if log_file:
            log_file_fn.close()

        if harvest_fetchers:
            harvest_fetchers.close()
            harvest_fetchers.terminate()

        print('TOTAL cycles:', cycles,
              'with:', total_defs_count, 'defs and combined harvests,',
              'in:', int(total_duration), 'sec.')


if __name__ == '__main__':
    cli()
