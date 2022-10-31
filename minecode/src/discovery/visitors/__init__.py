#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from functools import total_ordering
import gzip
import json
import os
import pkgutil
import tempfile

from discovery.utils import fetch_http
from discovery.utils import get_temp_file


# FIXME: use attr or use a plain ResourceURI object insteaad
@total_ordering
class URI(object):
    """
    Describe a URI to visit as returned by Visitors subclasses or visit
    functions. This mostly mirrors the ResourceURI models as a plain Python
    object.
    """
    __slots__ = (
        'uri',
        'source_uri',
        'package_url',
        'file_name',
        'size',
        'date',
        'md5',
        'sha1',
        'sha256',
        'priority',
        'data',
        'visited',
        'mining_level',
        'visit_error'
    )

    def __init__(self,
                 uri, source_uri=None, package_url=None,
                 file_name=None, size=None, date=None, md5=None, sha1=None, sha256=None,
                 priority=0,
                 data=None, visited=False, mining_level=0, visit_error=None, **kwargs
                 ):
        """
        Construct a new URI. A URI represents an address and extra information
        about this address at some point in time. `uri` is a mandatory URI
        string. All other arguments are optional.

        Most arguments mirror the ResourceURI model: see this for more details.
        Other arguments are:

         - `mining_level` is an int with a default to 0. This level indicates
           the the depth and breadth of the data provided by this visit. 0 means
           the basic, minimal level of mining, and bigger numbers indicate more
           depth and breadth of data. When merging the data from multiple
           visits, this is used to determine whether to update or replace
           attribute values.

         - `visited` is a boolean. If set to True, it means that this represents
           a visited URI. When this URI is process and eventually persisted as a
           ResourceURI the last_visit_date will be set to the current date if
           `visited` is True.

        NOTE: Unknown arguments are ignored!
        """
        self.uri = uri
        self.source_uri = source_uri
        self.package_url = package_url
        self.file_name = file_name
        self.size = size
        self.date = date
        self.md5 = md5
        self.sha1 = sha1
        self.sha256 = sha256
        self.priority = priority
        self.data = data
        self.visited = visited
        self.mining_level = mining_level
        self.visit_error = visit_error

    def to_dict(self, data_is_json=False):
        """
        Return an ordered seralization of self.
        Treat data as JSON if `data_is_json` is True
        """
        ordered_dict = dict()
        for k in self.__slots__:
            value = getattr(self, k)
            if value and data_is_json and k == 'data':
                value = json.loads(value)
            ordered_dict[k] = value
        return ordered_dict

    def __getitem__(self, item):
        return getattr(self, item)

    def __eq__(self, other):
        return isinstance(other, URI) and self.to_dict() == other.to_dict()

    def __lt__(self, other):
        return (isinstance(other, URI)
                and self.to_dict().items() < other.to_dict().items())

    def __repr__(self):
        args = [key + '=%(' + key + ')r' for key in self.__slots__
                if getattr(self, key, None)]
        return ('URI(' + ', '.join(args) + ')') % self.to_dict()

    @classmethod
    def from_db(cls, resource_uri):
        """
        Build a new URI from a ResourceURI model object.
        """
        kwargs = {}
        for key in cls.__slots__:
            value = getattr(resource_uri, key, None)
            if value:
                kwargs[key] = value

        return URI(**kwargs)


class Visitor(object):
    """
    Abstract base class for visitors. Subclasses must implement the fetch() and
    get_uris() methods and use a routing decorator for the URIs they can handle.
    """
    save_data = True

    def __call__(self, uri):
        """
        # FIXME: we need to pass a URI instance instead.
        Call this visitor passing a `uri` string.
        # TODO: update this doc
        returns iterable_of_uri_to_visit, data, errors?
        """
        # Note: we let exceptions bubble up and they will be caught and
        # processed by the worker loop
        self.uri = uri
        fetched_content = self.fetch(uri)
        content_object = self.loads(fetched_content)
        uris_to_visit = self.get_uris(content_object)
        # FIXME: we still use for now the old API returning [uris], data as a string, error
        # just for the transition
        return uris_to_visit, self.dumps(content_object), None

    def fetch(self, uri):
        """
        Fetch and return the content content found at a remote URI.
        """
        raise NotImplementedError

    def get_uris(self, content):
        """
        Given pre-fetched `content` available as a byte string (fetched from
        self.uri), this method must yield URI objects or return a list of URI
        objects.
        """
        return

    def dumps(self, content):
        """
        Return the content seralized as a string suitable for storing in a
        database text blob. Subclasses should override when they support
        structured content (such as JSON).
        """
        return content

    def loads(self, content):
        """
        Return a Python data structure loaded from a content seralized as a
        string either as fetched or loaded from the database. Subclasses should
        override when they support structured content (such as JSON).
        """
        return content


class HttpVisitor(Visitor):
    """
    Abstract base class for HTTP-based visitors. Subclasses must implement the
    get_uris() method and use a routing decorator for the URIs they can handle.
    """
    def fetch(self, uri, timeout=10):
        """
        Fetch and return the content found at a remote uri.
        `timeout` is a default timeout.
        """
        return fetch_http(uri, timeout=timeout)


class NonPersistentHttpVisitor(HttpVisitor):
    """
    Abstract base class for HTTP-based visitors that fetch a large file
    that is NOT stored in the DB but instead provided as a temporary
    file location.

    Subclasses must implement the get_uris() method. This get_uris()
    will receive a temporary file path in the content arg instead of the
    actual content at the URI and need to open and read this temporary
    file to obtain the content.
    """

    def fetch(self, uri, timeout=10):
        """
        Return a temporary location where the fetched content was saved.
        Does not return the content proper as a regular fetch does.

        `timeout` is a default timeout.
        """
        content = super(NonPersistentHttpVisitor, self).fetch(uri, timeout=timeout)
        temp_file = get_temp_file('NonPersistentHttpVisitor')
        with open(temp_file, 'wb') as tmp:
            tmp.write(content)
        return temp_file

    def dumps(self, content):
        """
        Return nothing. The content should not be saved.
        """
        return None


class HttpJsonVisitor(HttpVisitor):
    """
    Abstract base class for HTTP-based visitors that return JSON rather than
    plain HTML. Subclasses must implement the uris() method and use a routing
    decorator for the URIs they can handle.
    """

    def dumps(self, content):
        return json.dumps(content)

    def loads(self, content):
        return json.loads(content)


"""
Minimal way to recursively import all submodules dynamically. If this module is
imported, all submodules will be imported: this triggers the actual registration
of visitors.
This should stay as the last import in this init module.
"""
for _, name, _ in pkgutil.walk_packages(__path__, prefix=__name__ + '.'):
    __import__(name)
