#
# Copyright (c) by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

import logging
import sys
import traceback

from packagedcode.utils import combine_expressions

from matchcode.models import ApproximateDirectoryContentIndex
from matchcode.models import ApproximateDirectoryStructureIndex
from matchcode.models import ApproximateResourceContentIndex
from matchcode.models import ExactFileIndex
from matchcode.models import SnippetIndex
from matchcode.models import StemmedSnippetIndex
from minecode.management.commands import get_error_message
from minecode.model_utils import update_or_create_resource
from minecode.models import ScannableURI

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def index_package_files(package, scan_data, reindex=False):
    """
    Index scan data for `package` Package.

    Return a list of scan index errors messages

    If `reindex` is True, then all fingerprints related to `package` will be
    deleted and recreated from `scan_data`.
    """
    if reindex:
        logger.info(f"Deleting fingerprints and Resources related to {package.package_url}")
        package.approximatedirectorycontentindex_set.all().delete()
        package.approximatedirectorystructureindex_set.all().delete()
        package.approximateresourcecontentindex_set.all().delete()
        package.exactfileindex_set.all().delete()
        package.snippetindex_set.all().delete()
        package.stemmedsnippetindex_set.all().delete()
        package.resources.all().delete()

    scan_index_errors = []
    try:
        logger.info(
            f"Indexing Resources and fingerprints related to {package.package_url} from scan data"
        )
        for resource in scan_data.get("files", []):
            r, _, _ = update_or_create_resource(package, resource)
            path = r.path
            sha1 = r.sha1
            if sha1:
                _, _ = ExactFileIndex.index(sha1=sha1, package=package)

            resource_extra_data = resource.get("extra_data", {})

            directory_content_fingerprint = resource_extra_data.get("directory_content", "")
            if directory_content_fingerprint:
                _, _ = ApproximateDirectoryContentIndex.index(
                    fingerprint=directory_content_fingerprint,
                    resource_path=path,
                    package=package,
                )

            directory_structure_fingerprint = resource_extra_data.get("directory_structure", "")

            if directory_structure_fingerprint:
                _, _ = ApproximateDirectoryStructureIndex.index(
                    fingerprint=directory_structure_fingerprint,
                    resource_path=path,
                    package=package,
                )

            halo1 = resource_extra_data.get("halo1", "")
            if halo1:
                _, _ = ApproximateResourceContentIndex.index(
                    fingerprint=halo1,
                    resource_path=path,
                    package=package,
                )

            snippets = resource_extra_data.get("snippets", [])
            if snippets:
                for s in snippets:
                    snippet = s["snippet"]
                    position = s["position"]
                    _, _ = SnippetIndex.index(
                        fingerprint=snippet,
                        position=position,
                        resource=r,
                        package=package,
                    )

            stemmed_snippets = resource_extra_data.get("stemmed_snippets", [])
            if stemmed_snippets:
                for s in stemmed_snippets:
                    snippet = s["snippet"]
                    position = s["position"]
                    _, _ = StemmedSnippetIndex.index(
                        fingerprint=snippet,
                        position=position,
                        resource=r,
                        package=package,
                    )

    except Exception as e:
        msg = get_error_message(e)
        scan_index_errors.append(msg)
        logger.error(msg)

    return scan_index_errors


def update_package_relationships(package, existing_package):
    """
    Update the relations of `existing_package` to point at `package`
    """
    existing_package.approximatedirectorycontentindex_set.update(package=package)
    existing_package.approximatedirectorystructureindex_set.update(package=package)
    existing_package.approximateresourcecontentindex_set.update(package=package)
    existing_package.exactfileindex_set.update(package=package)
    existing_package.snippetindex_set.update(package=package)
    existing_package.stemmedsnippetindex_set.update(package=package)
    existing_package.resources.update(package=package)
    existing_package.is_duplicate = True
    existing_package.save()
    package.is_duplicate = False
    package.save()


def check_for_duplicate_packages(package):
    """
    Given a `package`, check to see if it has already been indexed already. If
    so, then check to see if `package` is a better candidate than the existing
    package for being the ultimate source for that package.

    Return True if a duplicate package already exists and relations have been
    updated, otherwise return False.
    """
    from packagedb.models import Package

    if not package.sha1:
        return False

    repo_types = [
        "apache",
        "bower",
        "composer",
        "cpan",
        "cran",
        "crate",
        "deb",
        "docker",
        "eclipse",
        "fdroid",
        "gem",
        "golang",
        "gstreamer",
        "maven",
        "npm",
        "nuget",
        "openwrt",
        "pypi",
        "rpm",
    ]
    source_repo_types = [
        "bitbucket",
        "github",
        "gitlab",
        "googlecode",
        "sourceforge",
    ]

    # Check for dupes
    existing_packages = Package.objects.filter(sha1=package.sha1, is_duplicate=False)
    for existing_package in existing_packages:
        # see if the package we are indexing is older than the package we have
        # TODO: This will probably have to be a task
        if (
            (package.type in repo_types and existing_package.type not in repo_types)
            or (
                package.type in source_repo_types and existing_package.type not in source_repo_types
            )
            or (
                (existing_package.release_date and package.release_date)
                and (existing_package.release_date > package.release_date)
            )
        ):
            update_package_relationships(package=package, existing_package=existing_package)

    return bool(existing_packages)


def index_package(
    scannable_uri, package, scan_data, summary_data, project_extra_data, reindex=False
):
    if check_for_duplicate_packages(package):
        return

    scan_index_errors = []
    try:
        indexing_errors = index_package_files(package, scan_data, reindex=reindex)
        scan_index_errors.extend(indexing_errors)
        declared_license_expression = summary_data.get("declared_license_expression")
        other_license_expressions = summary_data.get("other_license_expressions", [])
        other_license_expressions = [
            license_expression["value"]
            for license_expression in other_license_expressions
            if license_expression["value"]
        ]
        other_license_expression = combine_expressions(other_license_expressions)

        copyright = ""
        declared_holder = summary_data.get("declared_holder")
        if declared_holder:
            copyright = f"Copyright (c) {declared_holder}"

        checksums_and_size_by_field = {
            k: v
            for k, v in project_extra_data.items()
            if k in ["md5", "sha1", "size", "sha256", "sha512", "filename"]
        }
        values_by_updateable_fields = {
            "summary": summary_data,
            "declared_license_expression": declared_license_expression,
            "other_license_expression": other_license_expression,
            "copyright": copyright,
            **checksums_and_size_by_field,
        }
        # do not override fields with empty values
        values_by_updateable_fields = {k: v for k, v in values_by_updateable_fields.items() if v}

        _, updated_fields = package.update_fields(save=True, **values_by_updateable_fields)
        updated_fields = ", ".join(updated_fields)
        message = f"Updated fields for Package {package.purl}: {updated_fields}"
        logger.info(message)
        scannable_uri.scan_status = ScannableURI.SCAN_INDEXED
        scannable_uri.save()
    except Exception:
        traceback_message = traceback.format_exc()
        error_message = traceback_message + "\n"
        # TODO: We should rerun the specific indexers that have failed
        if scan_index_errors:
            error_message += "\n".join(scan_index_errors)
        logger.error(error_message)
        scannable_uri.index_error = error_message
        scannable_uri.scan_status = ScannableURI.SCAN_INDEX_FAILED
        scannable_uri.save()
