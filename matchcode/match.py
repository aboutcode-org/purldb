#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import sys
from functools import reduce
from operator import or_

from django.db.models import Q

import attr
from commoncode.resource import VirtualCodebase
from matchcode_toolkit.fingerprinting import compute_codebase_directory_fingerprints

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ApproximateResourceContentIndex
from matchcode.models import ExactFileIndex
from matchcode.models import ExactPackageArchiveIndex

TRACE = False

if TRACE:
    level = logging.DEBUG
else:
    level = logging.ERROR

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(level)


def logger_debug(*args):
    return logger.debug(" ".join(isinstance(a, str) and a or repr(a) for a in args))


"""
These functions are convenience functions to run matching on a Codebase or
VirtualCodebase for the purpose of testing. The functions that are used for
matching are in `matchcode_pipeline/pipes/matching.py`.
"""

EXACT_PACKAGE_ARCHIVE_MATCH = 0
APPROXIMATE_DIRECTORY_STRUCTURE_MATCH = 1
APPROXIMATE_DIRECTORY_CONTENT_MATCH = 2
EXACT_FILE_MATCH = 3
APPROXIMATE_FILE_MATCH = 4


def get_matchers():
    MATCHERS_BY_MATCH_TYPE = {
        EXACT_PACKAGE_ARCHIVE_MATCH: package_archive_match,
        APPROXIMATE_DIRECTORY_CONTENT_MATCH: approximate_directory_content_match,
        APPROXIMATE_DIRECTORY_STRUCTURE_MATCH: approximate_directory_structure_match,
        EXACT_FILE_MATCH: individual_file_match,
        APPROXIMATE_FILE_MATCH: approximate_file_match,
    }
    return MATCHERS_BY_MATCH_TYPE


def do_match(codebase, match_type):
    """
    Perform Package matching on `codebase` by running matching functions of
    `match_type` on `codebase`.

    The total number of matches found is returned.
    """
    matcher = get_matchers().get(match_type)
    if not matcher:
        raise Exception(f"Unknown match type: {match_type}")
    match_count = matcher(codebase)
    return match_count


def run_do_match_from_scan(scan_file_location, match_type):
    vc = VirtualCodebase(
        location=scan_file_location,
        codebase_attributes=dict(matches=attr.ib(default=attr.Factory(list))),
        resource_attributes=dict(matched_to=attr.ib(default=attr.Factory(list))),
    )
    vc = compute_codebase_directory_fingerprints(vc)
    do_match(vc, match_type)
    return vc


def package_archive_match(codebase):
    """
    Update Matches from detected Package Archives in `codebase`

    Return the number of matches found in `codebase`
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if (
            resource.is_dir
            or not resource.is_archive
            or resource.extra_data.get("matched", False)
        ):
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
        if resource.is_file or resource.extra_data.get("matched", False):
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
        if resource.is_file or resource.extra_data.get("matched", False):
            continue

        directory_matches, match_type = get_directory_structure_match(resource)
        if not directory_matches:
            continue

        match_count += directory_matches.count()
        tag_matched_resources(resource, codebase, directory_matches, match_type)
    return match_count


def individual_file_match(codebase):
    """
    Update Matches from detected Package files in `codebase`.

    Return the number of matches found in `codebase`.
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if resource.is_dir or resource.extra_data.get("matched", False):
            continue

        file_matches, match_type = get_file_match(resource)
        if not file_matches:
            continue

        match_count += len(file_matches)
        tag_matched_resources(resource, codebase, file_matches, match_type)
    return match_count


def approximate_file_match(codebase):
    """
    Update Matches from approximatly matched Package files in `codebase`.

    Return  the number of approximate matches found in `codebase`.
    """
    match_count = 0
    for resource in codebase.walk(topdown=True):
        if resource.is_dir or resource.extra_data.get("matched", False):
            continue
        file_matches, match_type = get_approximate_file_match(resource)
        if not file_matches:
            continue

        match_count += len(file_matches)
        tag_matched_resources(resource, codebase, file_matches, match_type)
    return match_count


def get_directory_content_match(resource):
    """Match a directory to a Package using its contents"""
    directory_content_fingerprint = resource.extra_data.get("directory_content", "")
    matches = ApproximateDirectoryContentIndex.objects.none()
    match_type = ""
    if directory_content_fingerprint:
        directory_matches = ApproximateDirectoryContentIndex.match(
            directory_content_fingerprint, resource
        )
        matches |= directory_matches
        match_type = "approximate-content"
    return matches, match_type


# TODO: rename match_directory_structure
def get_directory_structure_match(resource):
    """Match a directory to a Package using its structure"""
    directory_structure_fingerprint = resource.extra_data.get("directory_structure", "")
    matches = ApproximateDirectoryStructureIndex.objects.none()
    match_type = ""
    if directory_structure_fingerprint:
        directory_matches = ApproximateDirectoryStructureIndex.match(
            directory_structure_fingerprint, resource
        )
        matches |= directory_matches
        match_type = "approximate-structure"
    return matches, match_type


def get_archive_match(resource):
    """Match an Archive resource to a Package"""
    file_matches = ExactPackageArchiveIndex.match(resource.sha1)
    return file_matches, "exact-archive"


def get_file_match(resource):
    """Match an individual file back to the Package it is from"""
    file_matches = ExactFileIndex.match(resource.sha1)
    return file_matches, "exact-file"


def get_approximate_file_match(resource):
    """Approximately match an individual file back to the Package it is from"""
    if hasattr(resource, "halo1"):
        resource_content_fingerprint = resource.halo1
    else:
        resource_content_fingerprint = resource.extra_data.get("halo1", "")
    file_matches = ApproximateResourceContentIndex.match(
        resource_content_fingerprint, resource
    )
    return file_matches, "approximate-file"


def tag_matched_resource(resource, codebase, purl):
    """
    Set a resource to be flagged as matched, so it will not be considered in
    subsequent matches once it has been matched
    """
    if purl not in resource.matched_to:
        resource.matched_to.append(purl)
    resource.extra_data["matched"] = True
    resource.save(codebase)


def tag_matched_resources(resource, codebase, matches, match_type):
    """
    Tag this directory and other Resources under this directory so they are not
    candidates for matching by checking to see if a Resource path from
    `resource` or its children exists in the matched packages in `matches`
    """
    for match in matches:
        # Prep matched package data and append to `codebase`
        matched_package_info = match.package.to_dict()
        matched_package_info["match_type"] = match_type
        codebase.attributes.matches.append(matched_package_info)

        purl = match.package.package_url
        # Tag the Resource where we found a match
        tag_matched_resource(resource, codebase, purl)

        # Find matching package child path for `resource` by creating all possible
        # path suffixes from `child.path`, chaining them in Q objects (joined
        # by or), then querying the matched packages resources to see if any of
        # those suffixes match a package child resource path
        for child in resource.walk(codebase):
            query = reduce(
                or_, (Q(path=suffix) for suffix in path_suffixes(child.path)), Q()
            )
            matched_child_resources = match.package.resources.filter(query)
            if len(matched_child_resources) > 0:
                tag_matched_resource(child, codebase, purl)


def path_suffixes(path):
    """Yield all the suffixes of `path`, starting from the longest (e.g. more segments)."""
    segments = path.strip("/").split("/")
    suffixes = (segments[i:] for i in range(len(segments)))
    for suffix in suffixes:
        yield "/".join(suffix)


def merge_matches(matches, max_dist=None, trace=TRACE):
    """
    Return a list of merged LicenseMatch matches given a `matches` list of
    LicenseMatch. Merging is a "lossless" operation that combines two or more
    matches to the same rule and that are in sequence of increasing query and
    index positions in a single new match.
    """
    # shortcut for single matches
    if len(matches) < 2:
        return matches

    # only merge matches from the same package - package resource combination
    # sort by package, resource, sort on start, longer high, longer match, matcher type
    sorter = lambda m: (
        m.ipackage,
        m.iresource,
        m.qspan.start,
        -m.hilen(),
        -m.len(),
        m.matcher_order,
    )
    matches.sort(key=sorter)

    if trace:
        print("merge_matches: number of matches to process:", len(matches))

    if max_dist is None:
        # Using window length
        # TODO: expose window length variable and reference that here
        max_dist = 16

    # compare two matches in the sorted sequence: current and next
    i = 0
    while i < len(matches) - 1:
        j = i + 1
        while j < len(matches):
            current_match = matches[i]
            next_match = matches[j]

            # if we have two equal ispans and some overlap
            # keep the shortest/densest match in qspan e.g. the smallest magnitude of the two
            if current_match.ispan == next_match.ispan and current_match.overlap(
                next_match
            ):
                cqmag = current_match.qspan.magnitude()
                nqmag = next_match.qspan.magnitude()
                if cqmag <= nqmag:
                    if trace:
                        logger_debug(
                            "    ---> ###merge_matches: "
                            "current ispan EQUALS next ispan, current qmagnitude smaller, "
                            "del next"
                        )

                    del matches[j]
                    continue
                else:
                    if trace:
                        logger_debug(
                            "    ---> ###merge_matches: "
                            "current ispan EQUALS next ispan, next qmagnitude smaller, "
                            "del current"
                        )

                    del matches[i]
                    i -= 1
                    break

            # remove contained matches
            if current_match.qcontains(next_match):
                if trace:
                    logger_debug(
                        "    ---> ###merge_matches: "
                        "next CONTAINED in current, "
                        "del next"
                    )

                del matches[j]
                continue

            # remove contained matches the other way
            if next_match.qcontains(current_match):
                if trace:
                    logger_debug(
                        "    ---> ###merge_matches: "
                        "current CONTAINED in next, "
                        "del current"
                    )

                del matches[i]
                i -= 1
                break

            # FIXME: qsurround is too weak. We want to check also isurround
            # merge surrounded
            if current_match.surround(next_match):
                new_match = current_match.combine(next_match)
                if len(new_match.qspan) == len(new_match.ispan):
                    # the merged matched is likely aligned
                    current_match.update(next_match)
                    if trace:
                        logger_debug(
                            "    ---> ###merge_matches: "
                            "current SURROUNDS next, "
                            "merged as new:",
                            current_match,
                        )

                    del matches[j]
                    continue

            # FIXME: qsurround is too weak. We want to check also isurround
            # merge surrounded the other way too: merge in current
            if next_match.surround(current_match):
                new_match = current_match.combine(next_match)
                if len(new_match.qspan) == len(new_match.ispan):
                    # the merged matched is likely aligned
                    next_match.update(current_match)
                    if trace:
                        logger_debug(
                            "    ---> ###merge_matches: "
                            "next SURROUNDS current, "
                            "merged as new:",
                            current_match,
                        )

                    del matches[i]
                    i -= 1
                    break

            # FIXME: what about the distance??

            # next_match is strictly in increasing sequence: merge in current
            if next_match.is_after(current_match):
                current_match.update(next_match)
                if trace:
                    logger_debug(
                        "    ---> ###merge_matches: "
                        "next follows current, "
                        "merged as new:",
                        current_match,
                    )

                del matches[j]
                continue

            # next_match overlaps
            # Check increasing sequence and overlap importance to decide merge
            if (
                current_match.qstart <= next_match.qstart
                and current_match.qend <= next_match.qend
                and current_match.istart <= next_match.istart
                and current_match.iend <= next_match.iend
            ):
                qoverlap = current_match.qspan.overlap(next_match.qspan)
                if qoverlap:
                    ioverlap = current_match.ispan.overlap(next_match.ispan)
                    # only merge if overlaps are equals (otherwise they are not aligned)
                    if qoverlap == ioverlap:
                        current_match.update(next_match)

                        if trace:
                            logger_debug(
                                "    ---> ###merge_matches: "
                                "next overlaps in sequence current, "
                                "merged as new:",
                                current_match,
                            )

                        del matches[j]
                        continue

            j += 1
        i += 1
    print(matches)
    return matches
