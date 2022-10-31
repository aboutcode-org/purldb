#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import hashlib
import logging
import os
import tempfile

from django.conf import settings
from django.utils.encoding import force_str

import arrow
from arrow.parser import ParserError
import requests
from requests.exceptions import InvalidSchema
from requests.exceptions import ConnectionError

from commoncode.fileutils import create_dir
from extractcode.extract import extract

from discovery.management.commands import get_settings

logger = logging.getLogger(__name__)
# import sys
# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
# logger.setLevel(logging.DEBUG)


def stringify_null_purl_fields(data):
    """
    Modify `data` in place by ensuring `purl` fields are not None. This is useful for
    cleaning data before saving to db.
    """
    purl_fields = ('type', 'namespace', 'name', 'version', 'qualifiers', 'subpath')
    for field in purl_fields:
        try:
            if not data[field]:
                data[field] = ''
        except KeyError:
            continue


def sha1(content):
    """
    Returns the sha1 hash of the given content.
    """
    h = hashlib.sha1()
    h.update(content)
    return h.hexdigest()


def md5(content):
    """
    Returns the md5 hash of the given content.
    """
    h = hashlib.md5()
    h.update(content)
    return h.hexdigest()


class DataObject(object):
    """
    A data object, using attributes for storage and a to_dict method to get
    a dict back.
    """
    def __init__(self, defaults=None, **kw):
        if defaults:
            for k, v in defaults.items():
                setattr(self, k, v)

        for k, v in kw.items():
            setattr(self, k, v)

    def to_dict(self):
        return dict(self.__dict__)

    def __getitem__(self, item):
        return self.__dict__.get(item)

    def __eq__(self, other):
        return (
            self.to_dict(other.to_dict())
        )


def normalize_trailing_slash(uri):
    """
    Appends a trailing slash if the URI is not ending with one already.
    """
    if not uri.endswith('/'):
        uri += '/'
    return uri


def is_ascii(s):
    """
    Returns True is the string is ASCII.
    """
    return all(ord(c) < 128 for c in s)


def clean_html_entities(text):
    """
    Reverse of django.utils.html.escape
    """
    return text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')\
               .replace('&quot;', '"').replace('&#39;', "'")


def clean_description(text):
    """
    Cleans the description text from HTML entities and from extra whitespaces.
    """
    return ' '.join(clean_html_entities(text.strip()).split())


def strip_nbsp(s):
    """
    Replace non breaking space HTML entities with regular space and strip the
    string.
    """
    return force_str(s).replace('&nbsp;', ' ').strip()


CR = '\r'
LF = '\n'
CRLF = CR + LF
CRLF_NO_CR = ' ' + LF


def unixlinesep(text, preserve=False):
    """
    Normalize a string to Unix line separators. Preserve character offset by
    replacing with spaces if preserve is True.

    For example:
    >>> t=CR+LF+LF+CR+CR+LF
    >>> unixlinesep(t) == LF+LF+LF+LF
    True
    >>> unixlinesep(t, True) == ' '+LF+LF+LF+' '+LF
    True
    """
    return text.replace(CRLF, CRLF_NO_CR if preserve else LF).replace(CR, LF)


def decode_fuzzy_date(s, _self=None):
    """
    Parse a (possibly) fuzzy date and return an UTC ISO timestamp.

    If base is not None, fuzzy dates are resolved relative to this base date:
    this is used in testing. self is used only for testing such that the
    function can refer to itself This is a funky business but when testing,
    using fixed time bases is the only sane way.
    Raise an arrow.parser.ParserError RuntimeError if the date cannot be parsed
    """
    import dateutil

    if hasattr(_self, 'testing'):
        # fixed base date used only for testing for well defined date offsets
        base = arrow.get(2014, 2, 2)
    else:
        # general case
        base = arrow.utcnow()

    fuzzy = {
        'Last 30 days': -30,
        'Last 7 days': -7,
        'Today': 0,
        'Yesterday': -1,
    }

    formats = [
        'YYYY-MM-DD HH:mm:ss',

        'MMM DD, YYYY',
        'MMM D, YYYY',

        'ddd MMM D HH:mm:ss YYYY',
        'ddd MMM D H:mm:ss YYYY',
        'ddd MMM DD HH:mm:ss YYYY',
        'ddd MMM DD H:mm:ss YYYY',
        'dddd MMM D HH:mm:ss YYYY',
        'dddd MMM D H:mm:ss YYYY',
        'dddd MMM DD HH:mm:ss YYYY',
        'dddd MMM DD H:mm:ss YYYY',

        'MM/DD/YYYY',
    ]

    # normalize spaces
    s = ' '.join(s.split())
    if s == 'Earlier this year':
        ar = base.floor('year')
    elif s in fuzzy:
        ar = base.replace(days=fuzzy[s])
    else:
        ar = arrow.get(s, formats)
        ar = ar.replace(tzinfo=dateutil.tz.tzutc()).to('utc')  # NOQA
    return ar.isoformat()


def fetch_http(uri, timeout=10):
    """
    Fetch and return the content from an HTTP uri as raw byte string.
    `timeout` is a timeout with precedence over REQUESTS_ARGS settings.
    """
    return get_http_response(uri, timeout).content


def get_http_response(uri, timeout=10):
    """
    Fetch and return the response object from an HTTP uri.
    `timeout` is a timeout with precedence over REQUESTS_ARGS settings.
    """
    requests_args = getattr(settings, 'REQUESTS_ARGS', {})
    requests_args['timeout'] = timeout

    if not uri.lower().startswith('http'):
        raise Exception('get_http_response: Not an HTTP URI: %(uri)r' % locals())

    try:
        response = requests.get(uri, **requests_args)
    except (ConnectionError, InvalidSchema) as e:
        logger.error('get_http_response: Download failed for %(uri)r' % locals())
        raise

    status = response.status_code
    if status != 200:
        raise Exception('get_http_response: Download failed for %(uri)r '
                        'with %(status)r' % locals())
    return response


def system_temp_dir(temp_dir=os.getenv('MINECODE_TMP')):
    """
    Return the global temp directory..
    """
    if not temp_dir:
        temp_dir = os.path.join(tempfile.gettempdir(), 'minecode')
    create_dir(temp_dir)
    return temp_dir


def get_temp_dir(base_dir='', prefix=''):
    """
    Return the path to base a new unique temporary directory, created under
    the system-wide `system_temp_dir` temp directory and as a subdir of the
    base_dir path, a path relative to the `system_temp_dir`.
    """
    if base_dir:
        base_dir = os.path.join(system_temp_dir(), base_dir)
        create_dir(base_dir)
    else:
        base_dir = system_temp_dir()
    return tempfile.mkdtemp(prefix=prefix, dir=base_dir)


def get_temp_file(file_name='data', extension='.file', dir_name=''):
    """
    Return a file path string to a new, unique and non-existing
    temporary file that can safely be created without a risk of name
    collision.
    """
    if extension and not extension.startswith('.'):
        extension = '.' + extension

    file_name = file_name + extension
    # create a new temp dir each time
    temp_dir = get_temp_dir(dir_name)
    location = os.path.join(temp_dir, file_name)
    return location


def extract_file(location):
    """
    Extract file at location returning the extracted location.
    """
    target = None
    try:
        for event in extract(location):
            if event.done:
                if event.warnings or event.errors:
                    raise Exception()
                target = event.target
                break
    except Exception as e:
        logger.error('extract_file: failed for %(location)r' % locals())
        raise e
    return target


def parse_date(s):
    """
    Return date string in YYYY-MM-DD format from a datetime string
    """
    if s:
        try:
            return arrow.get(s).format('YYYY-MM-DD')
        except ParserError:
            # If we can't parse a date, it's not a big deal as `release_date`
            # is not an important field for us
            return


def is_int(s):
    """To test if the input para is a int
    """
    try:
        int(s)
        return True
    except ValueError:
        return False


def form_vcs_url(vcs_tool, vcs_url, revision_tag_or_branch=None, sub_path=None):
    # Form the vsc_url by
    # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
    # <vcs_tool>+<transport>://<host_name>[/<path_to_repository>][@<revision_tag_or_branch>][#<sub_path>]
    if vcs_url:
        if vcs_tool:
            vcs_url = '+'.join(str(v) for v in [vcs_tool, vcs_url])
        if revision_tag_or_branch:
            vcs_url = '@'.join(str(v) for v in [vcs_url, revision_tag_or_branch])
        if sub_path:
            vcs_url = '#'.join(str(v) for v in [vcs_url, sub_path])
    return vcs_url
