#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from minecode import seed
from minecode import rsync
from minecode import visit_router
from minecode.miners import URI

"""
Collect YUM repositories index (aka. repodata) from CentOS, Fedora, openSUSE and
other repos.
"""

rsync_urls = (
    'rsync://mirrors.kernel.org/centos/',
    'rsync://yum.postgresql.org',
    'rsync://www.fedora.is/fedora/',
    'rsync://rsync.opensuse.org/',
)


class RPMRepoDataSeed(seed.Seeder):

    def get_seeds(self):
        yield 'rsync://mirrors.kernel.org/centos/'
        yield 'rsync://yum.postgresql.org'
        yield 'rsync://www.fedora.is/fedora/'
        yield 'rsync://rsync.opensuse.org/'


def collect_rsync_urls(directory_listing, base_url, file_names=('repomd.xml',)):
    """
    Given an rsync URI that may contain files with path ending with
    any of the 'path_ends' tuple yield URIs using the 'base_url' as the base.
    """
    # FIXME: why this assert?

    for entry in rsync.directory_entries(directory_listing):
        # FIXME: why this assert?
        assert not entry['path'].startswith('/')
        if entry['path'].endswith(file_names):
            entry = base_url + entry['path']
            yield URI(uri=entry)


@visit_router.route(*rsync_urls)
def collect_repomd_urls(uri, file_names=('repomd.xml',)):
    directory_listing = rsync.fetch_directory(uri)
    return collect_rsync_urls(directory_listing, base_url=uri.replace('rsync://', 'http://'), file_names=file_names), None, None
