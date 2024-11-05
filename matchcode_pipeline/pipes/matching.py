# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

from collections import defaultdict

from django.db.models import Q
from django.template.defaultfilters import pluralize

from aboutcode.pipeline import LoopProgress
from scanpipe import pipes
from scanpipe.pipes import flag
from scanpipe.pipes import js

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateResourceContentIndex
from packagedb.models import Package
from packagedb.models import Resource


def get_project_resources_qs(project, resources):
    """
    Return a queryset of CodebaseResources from `project` containing the
    CodebaseResources from `resources` . If a CodebaseResource in `resources` is
    an archive or directory, then their descendants are also included in the
    queryset.

    Return None if `resources` is empty or None.
    """
    lookups = Q()
    for resource in resources or []:
        lookups |= Q(path=resource.path)
        if resource.is_archive:
            # This is done to capture the extracted contents of the archive we
            # matched to. Generally, the archive contents are in a directory
            # that is the archive path with `-extract` at the end.
            lookups |= Q(path__startswith=resource.path)
        elif resource.is_dir:
            # We add a trailing slash to avoid matching on directories we do not
            # intend to. For example, if we have matched on the directory with
            # the path `foo/bar/1`, using the __startswith filter without
            # including a trailing slash on the path would have us get all
            # diretories under `foo/bar/` that start with 1, such as
            # `foo/bar/10001`, `foo/bar/123`, etc., when we just want `foo/bar/1`
            # and its descendants.
            path = f"{resource.path}/"
            lookups |= Q(path__startswith=path)
    if lookups:
        return project.codebaseresources.filter(lookups)


def create_package_from_purldb_data(project, resources, package_data, status):
    """
    Create a DiscoveredPackage instance from PurlDB ``package_data``.

    Return a tuple, containing the created DiscoveredPackage and the number of
    CodebaseResources matched to PurlDB that are part of that DiscoveredPackage.
    """
    package_data = package_data.copy()
    # Do not re-use uuid from PurlDB as DiscoveredPackage.uuid is unique and a
    # PurlDB match can be found in different projects.
    package_data.pop("uuid", None)
    package_data.pop("dependencies", None)

    resources_qs = get_project_resources_qs(project, resources)
    package = pipes.update_or_create_package(
        project=project,
        package_data=package_data,
        codebase_resources=resources_qs,
    )
    # Get the number of already matched CodebaseResources from `resources_qs`
    # before we update the status of all CodebaseResources from `resources_qs`,
    # then subtract the number of already matched CodebaseResources from the
    # total number of CodebaseResources updated. This is to prevent
    # double-counting of CodebaseResources that were matched to purldb
    purldb_statuses = [
        flag.MATCHED_TO_PURLDB_PACKAGE,
        flag.MATCHED_TO_PURLDB_RESOURCE,
        flag.MATCHED_TO_PURLDB_DIRECTORY,
    ]
    matched_resources_count = resources_qs.exclude(status__in=purldb_statuses).update(
        status=status
    )
    return package, matched_resources_count


def match_purldb_package(
    project, resources_by_sha1, enhance_package_data=True, **kwargs
):
    """
    Given a mapping of lists of CodebaseResources by their sha1 values,
    `resources_by_sha1`, send those sha1 values to purldb packages API endpoint,
    process the matched Package data, then return the number of
    CodebaseResources that were matched to a Package.
    """
    match_count = 0
    sha1_list = list(resources_by_sha1.keys())
    results = Package.objects.using("packagedb").filter(sha1__in=sha1_list)
    # Process matched Package data
    for package in results:
        package_data = package.to_dict()
        sha1 = package_data["sha1"]
        resources = resources_by_sha1.get(sha1) or []
        if not resources:
            continue
        _, matched_resources_count = create_package_from_purldb_data(
            project=project,
            resources=resources,
            package_data=package_data,
            status=flag.MATCHED_TO_PURLDB_PACKAGE,
        )
        match_count += matched_resources_count
    return match_count


def match_purldb_resource(
    project, resources_by_sha1, package_data_by_purldb_urls=None, **kwargs
):
    """
    Given a mapping of lists of CodebaseResources by their sha1 values,
    `resources_by_sha1`, send those sha1 values to purldb resources API
    endpoint, process the matched Package data, then return the number of
    CodebaseResources that were matched to a Package.

    `package_data_by_purldb_urls` is a mapping of package data by their purldb
    package instance URLs. This is intended to be used as a cache, to avoid
    retrieving package data we retrieved before.
    """
    package_data_by_purldb_urls = package_data_by_purldb_urls or {}
    match_count = 0
    sha1_list = list(resources_by_sha1.keys())
    results = Resource.objects.using("packagedb").filter(sha1__in=sha1_list)
    # Process match results
    for resource in results:
        # Get package data
        package_data = resource.package.to_dict()
        sha1 = resource.sha1
        resources = resources_by_sha1.get(sha1) or []
        if not resources:
            continue
        _, matched_resources_count = create_package_from_purldb_data(
            project=project,
            resources=resources,
            package_data=package_data,
            status=flag.MATCHED_TO_PURLDB_RESOURCE,
        )
        match_count += matched_resources_count
    return match_count


def match_purldb_resource_approximately(project, resource):
    """Match by approximation a single resource in the PurlDB."""
    fingerprint = resource.extra_data.get("halo1", "")
    results = ApproximateResourceContentIndex.match(
        fingerprint=fingerprint, resource=resource
    )
    for result in results:
        package_data = result.package.to_dict()
        return create_package_from_purldb_data(
            project,
            [resource],
            package_data,
            flag.APPROXIMATE_MATCHED_TO_PURLDB_RESOURCE,
        )


def match_purldb_directory(project, resource, exact_match=False):
    """Match a single directory resource in the PurlDB."""
    fingerprint = resource.extra_data.get("directory_content", "")
    results = ApproximateDirectoryContentIndex.match(
        fingerprint=fingerprint, resource=resource, exact_match=exact_match
    )
    for result in results:
        package_data = result.package.to_dict()
        return create_package_from_purldb_data(
            project, [resource], package_data, flag.MATCHED_TO_PURLDB_DIRECTORY
        )


def match_sha1s_to_purldb(
    project, resources_by_sha1, matcher_func, package_data_by_purldb_urls
):
    """
    Process `resources_by_sha1` with `matcher_func` and return a 3-tuple
    contaning an empty defaultdict(list), the number of matches and the number
    of sha1s sent to purldb.
    """
    matched_count = matcher_func(
        project=project,
        resources_by_sha1=resources_by_sha1,
        package_data_by_purldb_urls=package_data_by_purldb_urls,
    )
    sha1_count = len(resources_by_sha1)
    # Clear out resources_by_sha1 when we are done with the current batch of
    # CodebaseResources
    resources_by_sha1 = defaultdict(list)
    return resources_by_sha1, matched_count, sha1_count


def match_purldb_resources(
    project, matcher_func, archives_only=False, chunk_size=1000, logger=None
):
    """
    Match CodebaseResources from `project` against the PurlDB. If
    `archives_only` is True, then only CodebaseResources where the `is_archive`
    flag is True is looked up in the PurlDB.

    Match requests are sent off in batches of 1000 SHA1s. This number is set
    using `chunk_size`.
    """
    resources = (
        project.codebaseresources.files()
        .no_status(status=flag.MATCHED_TO_PURLDB_PACKAGE)
        .has_value("sha1")
        .filter(is_archive=archives_only)
    )
    resource_count = resources.count()

    if logger:
        if resource_count > 0:
            logger(f"Matching {resource_count:,d} resources in PurlDB, " "using SHA1")
        else:
            logger(f"Skipping resource matching as there are {resource_count:,d}")

    _match_purldb_resources(
        project=project,
        resources=resources,
        matcher_func=matcher_func,
        chunk_size=chunk_size,
        logger=logger,
    )


def _match_purldb_resources(
    project, resources, matcher_func, chunk_size=1000, logger=None
):
    resource_count = resources.count()
    resource_iterator = resources.iterator(chunk_size=chunk_size)
    progress = LoopProgress(resource_count, logger)
    total_matched_count = 0
    total_sha1_count = 0
    processed_resources_count = 0
    resources_by_sha1 = defaultdict(list)
    package_data_by_purldb_urls = {}

    for to_resource in progress.iter(resource_iterator):
        resources_by_sha1[to_resource.sha1].append(to_resource)
        if to_resource.path.endswith(".map"):
            for js_sha1 in js.source_content_sha1_list(to_resource):
                resources_by_sha1[js_sha1].append(to_resource)
        processed_resources_count += 1

        if processed_resources_count % chunk_size == 0:
            resources_by_sha1, matched_count, sha1_count = match_sha1s_to_purldb(
                project=project,
                resources_by_sha1=resources_by_sha1,
                matcher_func=matcher_func,
                package_data_by_purldb_urls=package_data_by_purldb_urls,
            )
            total_matched_count += matched_count
            total_sha1_count += sha1_count

    if resources_by_sha1:
        resources_by_sha1, matched_count, sha1_count = match_sha1s_to_purldb(
            project=project,
            resources_by_sha1=resources_by_sha1,
            matcher_func=matcher_func,
            package_data_by_purldb_urls=package_data_by_purldb_urls,
        )
        total_matched_count += matched_count
        total_sha1_count += sha1_count

    logger(
        f"{total_matched_count:,d} resources matched in PurlDB "
        f"using {total_sha1_count:,d} SHA1s"
    )


def match_purldb_resources_approximately(project, logger=None):
    # Get table of resources to match on
    resources = (
        project.codebaseresources.filter(is_text=True)
        .no_status(status=flag.MATCHED_TO_PURLDB_PACKAGE)
        .no_status(status=flag.MATCHED_TO_PURLDB_RESOURCE)
        .no_status(status=flag.MATCHED_TO_PURLDB_DIRECTORY)
    )
    resource_count = resources.count()

    if logger:
        logger(
            f"Approximate matching {resource_count:,d} "
            f"resource{pluralize(resource_count, 's')} against PurlDB"
        )

    resource_iterator = resources.iterator(chunk_size=2000)
    progress = LoopProgress(resource_count, logger)

    for resource in progress.iter(resource_iterator):
        match_purldb_resource_approximately(
            project,
            resource,
        )

    matched_count = project.codebaseresources.filter(
        status=flag.APPROXIMATE_MATCHED_TO_PURLDB_RESOURCE
    ).count()
    logger(
        f"{matched_count:,d} resource{pluralize(matched_count, 's')} "
        f"approximately matched in PurlDB"
    )


def match_purldb_directories(project, exact_directory_match=False, logger=None):
    """Match directory CodebaseResources from `project` against the PurlDB."""
    # If we are able to get match results for a directory fingerprint, then that
    # means every resource and directory under that directory is part of a
    # Package. By starting from the root to/ directory, we are attempting to
    # match as many files as we can before attempting to match further down. The
    # more "higher-up" directories we can match to means that we reduce the
    # number of queries made to purldb.
    directories = (
        project.codebaseresources.directories()
        .no_status(status=flag.MATCHED_TO_PURLDB_PACKAGE)
        .order_by("path")
    )
    directory_count = directories.count()

    if logger:
        logger(
            f"Matching {directory_count:,d} "
            f"director{pluralize(directory_count, 'y,ies')} against PurlDB"
        )

    directory_iterator = directories.iterator(chunk_size=2000)
    progress = LoopProgress(directory_count, logger)

    for directory in progress.iter(directory_iterator):
        directory.refresh_from_db()
        if directory.status != flag.MATCHED_TO_PURLDB_DIRECTORY:
            match_purldb_directory(project, directory, exact_directory_match)

    matched_count = (
        project.codebaseresources.directories()
        .filter(status=flag.MATCHED_TO_PURLDB_DIRECTORY)
        .count()
    )
    logger(
        f"{matched_count:,d} director{pluralize(matched_count, 'y,ies')} "
        f"matched in PurlDB"
    )


def match_purldb_resources_post_process(project, logger=None):
    """Choose the best package for PurlDB matched resources."""
    extract_directories = project.codebaseresources.directories().filter(
        path__regex=r"^.*-extract$"
    )

    resources = project.codebaseresources.files().filter(
        status=flag.MATCHED_TO_PURLDB_RESOURCE
    )

    resource_count = extract_directories.count()

    if logger:
        logger(
            f"Refining matching for {resource_count:,d} "
            f"{flag.MATCHED_TO_PURLDB_RESOURCE} archives."
        )

    resource_iterator = extract_directories.iterator(chunk_size=2000)
    progress = LoopProgress(resource_count, logger)
    map_count = 0

    for directory in progress.iter(resource_iterator):
        map_count += _match_purldb_resources_post_process(directory.path, resources)

    logger(f"{map_count:,d} resource processed")


def _match_purldb_resources_post_process(directory_path, codebase_resources):
    # Exclude the content of nested archive.
    interesting_codebase_resources = (
        codebase_resources.filter(path__startswith=directory_path)
        .filter(status=flag.MATCHED_TO_PURLDB_RESOURCE)
        .exclude(path__regex=rf"^{directory_path}.*-extract\/.*$")
    )

    if not interesting_codebase_resources:
        return 0

    packages_map = {}

    for resource in interesting_codebase_resources:
        for package in resource.discovered_packages.all():
            if package in packages_map:
                packages_map[package].append(resource)
            else:
                packages_map[package] = [resource]

    # Rank the packages by most number of matched resources.
    ranked_packages = dict(
        sorted(packages_map.items(), key=lambda item: len(item[1]), reverse=True)
    )

    for resource in interesting_codebase_resources:
        resource.discovered_packages.clear()

    for package, resources in ranked_packages.items():
        unmapped_resources = [
            resource
            for resource in resources
            if not resource.discovered_packages.exists()
        ]
        if unmapped_resources:
            package.add_resources(unmapped_resources)

    return interesting_codebase_resources.count()
