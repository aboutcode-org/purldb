#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from functools import reduce
from operator import or_

from django.db.models import Q

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ExactFileIndex
from matchcode.models import ExactPackageArchiveIndex


# TODO: Refactor this file into functions/utilities used in
# a scanpipe pipeline.
EXACT_PACKAGE_ARCHIVE_MATCH = 0
APPROXIMATE_DIRECTORY_STRUCTURE_MATCH = 1
APPROXIMATE_DIRECTORY_CONTENT_MATCH = 2
EXACT_FILE_MATCH = 3


def get_matchers():
    MATCHERS_BY_MATCH_TYPE = {
        EXACT_PACKAGE_ARCHIVE_MATCH: package_archive_match,
        APPROXIMATE_DIRECTORY_CONTENT_MATCH: approximate_directory_content_match,
        APPROXIMATE_DIRECTORY_STRUCTURE_MATCH: approximate_directory_structure_match,
        EXACT_FILE_MATCH: individual_file_match,
    }
    return MATCHERS_BY_MATCH_TYPE


def do_match(codebase, match_type):
    """
    Perform Package matching on `codebase` by running matching functions of `match_type` on `codebase`

    The total number of matches found is returned
    """

    matcher = get_matchers().get(match_type)
    if not matcher:
        raise Exception('Unknown match type: {}'.format(match_type))
    match_count = matcher(codebase)
    return match_count


def package_archive_match(codebase):
    """
    Update Matches from detected Package Archives in `codebase`

    Return the number of matches found in `codebase`
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if (resource.is_dir
                or not resource.is_archive
                or resource.extra_data.get('matched', False)):
            continue

        archive_matches, match_type = get_archive_match(resource)
        if not archive_matches:
            continue

        match_count += len(archive_matches)

        # Tag matched Resource as `matched` as to not analyze it later
        tag_matched_resources(resource, codebase, archive_matches, match_type)
    return match_count


def approximate_directory_content_match(codebase):
    """
    Update Matches from detected Package directories based on directory contents in `codebase`

    Return the number of matches found in `codebase`
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if resource.is_file or resource.extra_data.get('matched', False):
            continue

        directory_matches, match_type = get_directory_content_match(resource)
        if not directory_matches:
            continue

        match_count += directory_matches.count()
        tag_matched_resources(resource, codebase, directory_matches, match_type)
    return match_count


def approximate_directory_structure_match(codebase):
    """
    Update Matches from detected Package directories based on directory structure in `codebase`

    Return the number of matches found in `codebase`
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if resource.is_file or resource.extra_data.get('matched', False):
            continue

        directory_matches, match_type = get_directory_structure_match(resource)
        if not directory_matches:
            continue

        match_count += directory_matches.count()
        tag_matched_resources(resource, codebase, directory_matches, match_type)
    return match_count


def individual_file_match(codebase):
    """
    Update Matches from detected Package files in `codebase`

    Return the number of matches found in `codebase`
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if resource.is_dir or resource.extra_data.get('matched', False):
            continue

        file_matches, match_type = get_file_match(resource)
        if not file_matches:
            continue

        match_count += len(file_matches)
        tag_matched_resources(resource, codebase, file_matches, match_type)
    return match_count


def get_directory_content_match(resource):
    """
    Match a directory to a Package using its contents
    """
    directory_content_fingerprint = resource.extra_data.get('directory_content', '')
    matches = ApproximateDirectoryContentIndex.objects.none()
    match_type = ''
    if directory_content_fingerprint:
        directory_matches = ApproximateDirectoryContentIndex.match(directory_content_fingerprint)
        matches |= directory_matches
        match_type = 'approximate-content'
    return matches, match_type


# TODO: rename match_directory_structure
def get_directory_structure_match(resource):
    """
    Match a directory to a Package using its structure
    """
    directory_structure_fingerprint = resource.extra_data.get('directory_structure', '')
    matches = ApproximateDirectoryStructureIndex.objects.none()
    match_type = ''
    if directory_structure_fingerprint:
        directory_matches = ApproximateDirectoryStructureIndex.match(directory_structure_fingerprint)
        matches |= directory_matches
        match_type = 'approximate-structure'
    return matches, match_type


def get_archive_match(resource):
    """
    Match an Archive resource to a Package
    """
    file_matches = ExactPackageArchiveIndex.match(resource.sha1)
    return file_matches, 'exact-archive'


def get_file_match(resource):
    """
    Match an individual file back to the Package it is from
    """
    file_matches = ExactFileIndex.match(resource.sha1)
    return file_matches, 'exact-file'


def tag_matched_resource(resource, codebase, purl):
    """
    Set a resource to be flagged as matched, so it will not be considered in
    subsequent matches once it has been matched
    """
    if purl not in resource.matched_to:
        resource.matched_to.append(purl)
    resource.extra_data['matched'] = True
    resource.save(codebase)


def tag_matched_resources(resource, codebase, matches, match_type):
    """
    Tag this directory and other Resources under this directory so they are not
    candidates for matching by checking to see if a Resource path from
    `resource` or its children exists in the matched packages in `matches`
    """
    for match in matches:
        # Prep matched package data and append to `codebase`
        matched_package_info = match.package.package.to_dict()
        matched_package_info['match_type'] = match_type
        codebase.attributes.matches.append(matched_package_info)

        purl = match.package.package.package_url
        # Tag the Resource where we found a match
        tag_matched_resource(resource, codebase, purl)

        # Find matching package child path for `resource` by creating all possible
        # path suffixes from `child.path`, chaining them in Q objects (joined
        # by or), then querying the matched packages resources to see if any of
        # those suffixes match a package child resource path
        for child in resource.walk(codebase):
            query = reduce(or_, (Q(path=suffix) for suffix in path_suffixes(child.path)), Q())
            matched_child_resources = match.package.resources.filter(query)
            if len(matched_child_resources) > 0:
                tag_matched_resource(child, codebase, purl)


def path_suffixes(path):
    """
    Yield all the suffixes of `path`, starting from the longest (e.g. more segments).
    """
    segments = path.strip('/').split('/')
    suffixes = (segments[i:] for i in range(len(segments)))
    for suffix in suffixes:
        yield '/'.join(suffix)
