#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import re


VERSION_PATTERNS_REGEX = [re.compile(x, re.IGNORECASE) for x in [
    # v123413.feature_111.22.11.121
    'v\d+\.feature\_(\d+\.){1,3}\d+',

    # YYYY-MM-DD_12345
    '\d{4}-\d{2}-\d{2}_\d+',

    # FIXME: this a single regex that should be split
    '(M?(v\d+(\-|\_))?\d+\.){1,3}\d+[A-Za-z0-9]*'
    '((\.|\-|_|~)(b|B|rc|r|v|RC|alpha|beta|m|pre|vm|G)?\d+((\-|\.)\d+)?)?'
    '('
    '(\.|\-)'
    '('
    '('
    '(alpha|dev|beta|rc|final|pre)'
    '(\-|\_)\d+[A-Za-z]?(\-RELEASE)?'
    ')'
    '|alpha'
    '|dev(\.\d+\.\d+)?'
    '|beta|final|release|fixed'
    '|(cr\d(\_\d*)?)'
    ')'
    ')?',

    '[A-Za-z]?(\d+\_){1,3}\d+\_?[A-Za-z]{0,2}\d+',
    '(b|rc|r|v|RC|alpha|beta|m|pre|revision-)\d+(\-\d+)?',
    'current|previous|latest|alpha|beta',
    '\d+-\d+-\d+-\d+',
    '\d{4}-\d{2}-\d{2}',
    '\d+-\d+-\d+',
    '(\d(\-|\_)){1,2}\d',
    '\d{5,14}',
]]


def version_hint(path, ignore_pre_releases=False, remove_v_prefix=False):
    """
    Return a version found in a path or None. If ignore_pre_releases is True,
    then beta, alpha, pre, and rc versions are considered as the same as a non-
    beta version. For example: foo-1.2.0 and foo-1.2.0rc1 will both return
    1.2.0 as a version in this case.
    """
    stripped = strip_extensions(path)
    stripped = strip_version_tags(stripped)
    if not stripped:
        return
    for pattern in VERSION_PATTERNS_REGEX:
        segments = stripped.split('/')
        # skip the first path segment unless there's only one segment
        first_segment = 1 if len(segments) > 1 else 0
        interesting_segments = segments[first_segment:]
        # we iterate backwards from the end of the paths segments list
        for segment in interesting_segments[::-1]:
            version = re.search(pattern, segment)
            if version:
                vs = version.group(0)
                fixed = fix_packages_version(path, vs)
                if ignore_pre_releases:
                    fixed = strip_pre_releases(fixed)
                if remove_v_prefix and fixed.startswith('v'):
                    fixed = fixed[1:]
                return fixed


NON_VERSION_TAGS = ('win32', 'am64', 'x86_64', 'i386', 'i586', 'i586', 'x86',
                    'macosx',)

NON_VT_RES = [re.compile(re.escape(t), re.IGNORECASE) for t in NON_VERSION_TAGS]


def strip_version_tags(path):
    """Remove well known tags that are not part of the version."""
    for ret in NON_VT_RES:
        path = ret.sub('', path)
    return path


ARCHIVE_FILE_EXTENSIONS = (
    '.7z', '.7zip', '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz',
    '.tbz2', '.tz', '.txz', '.zip', '.rar', '.tar', '.gz', '.bz2', '.jar',
    '.tar.lzma', '.war', '.lib', '.a', '.ear', '.sar', '.tlz',
    '.xz', '.lzma', '.exe', '.rpm', '.deb', '.msi', '.z', '.pkg',
)


ARCHIVE_FILE_EXT_RES = [re.compile(re.escape(e) + '$', re.IGNORECASE)
                        for e in ARCHIVE_FILE_EXTENSIONS]


def strip_extensions(path):
    """"Remove well known archive extensions from end of path."""
    for rext in ARCHIVE_FILE_EXT_RES:
        path = rext.sub('', path)
    return path


# these extensions are used for common RPMs and Deb packages

PACKAGE_EXTENSIONS = ('.deb', '.rpm', '.srpm', '.diff.gz',)


def fix_packages_version(path, version_string):
    """
    Return a fixed version string stripping common -xxx paddings added for Deb
    and RPMs. For example the version of blueproximity-1.2.4-1.fc8.noarch.rpm
    becomes 1.2.4 instead of 1.2.4-1
    """
    if path.endswith(PACKAGE_EXTENSIONS):
        if version_string.count('-') == 1:
            left, _right = version_string.split('-')
            return left
    # return as-is in all other cases
    return version_string


PRE_RELEASE_TAGS = []


for pt in ('pre', 'rc', 'alpha', 'beta', 'b1', 'b2', 'b3', 'b4', 'b5'):
    # common punctuation prefixes before the tag
    for pp in ('_', '-', '.', '~',):
        # variants with prefix before the bare variant
        PRE_RELEASE_TAGS.append(pp + pt.upper())
        PRE_RELEASE_TAGS.append(pp + pt)
    # bare variant
    PRE_RELEASE_TAGS.append(pt.upper())
    PRE_RELEASE_TAGS.append(pt)


def strip_pre_releases(version_string):
    """
    Return a version string stripped from alpha, beta, rc and pre parts.
    """
    if not any(t in version_string for t in PRE_RELEASE_TAGS):
        return version_string
    for tag in PRE_RELEASE_TAGS:
        if tag not in version_string:
            continue
        splitted = version_string.split(tag)
        return splitted[0]
