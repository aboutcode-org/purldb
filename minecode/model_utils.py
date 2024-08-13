import copy
import logging
import sys

from django.utils import timezone

from commoncode import fileutils
from packagedcode.models import PackageData
from packageurl import normalize_qualifiers

from minecode.models import ScannableURI
from minecode.utils import stringify_null_purl_fields
from packagedb.models import DependentPackage
from packagedb.models import Package
from packagedb.models import PackageContentType
from packagedb.models import PackageSet
from packagedb.models import Party
from packagedb.models import Resource
from packagedb.serializers import DependentPackageSerializer
from packagedb.serializers import PartySerializer

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


# These are the list of default pipelines to run when we scan a Package for
# indexing
DEFAULT_PIPELINES = (
    "scan_single_package",
    "fingerprint_codebase",
)

# These are the list of supported addon pipelines to run when we scan a Package for
# indexing.
SUPPORTED_ADDON_PIPELINES = (
    "collect_strings_gettext",
    "collect_symbols_ctags",
    "collect_symbols_pygments",
    "collect_symbols_tree_sitter",
    "inspect_elf_binaries",
    "scan_for_virus",
)


def add_package_to_scan_queue(
    package, pipelines=DEFAULT_PIPELINES, priority=0, reindex_uri=False
):
    """
    Add a Package `package` to the scan queue to run the list of provided
    `pipelines` with a given `priority`. A ScannableURI with a `priority` of 100
    will be processed before a ScannableURI with a `priority` of 0.

    If `reindex_uri` is True, force rescanning of the package
    """
    if not pipelines:
        raise Exception("pipelines required to add package to scan queue")
    uri = package.download_url
    _, scannable_uri_created = ScannableURI.objects.get_or_create(
        uri=uri,
        pipelines=pipelines,
        package=package,
        reindex_uri=reindex_uri,
        priority=priority,
    )
    if scannable_uri_created:
        logger.debug(f" + Inserted ScannableURI\t: {uri}")


def merge_packages(existing_package, new_package_data, replace=False):
    """
    Merge the data from the `new_package_data` mapping into the
    `existing_package` Package model object.

    When an `existing_package` field has no value one side and and the
    new_package field has a value, the existing_package field is always
    set to this value.

    If `replace` is True and a field has a value on both sides, then
    existing_package field value will be replaced by the new_package
    field value. Otherwise if `replace` is False, the existing_package
    field value is left unchanged in this case.
    """
    existing_mapping = existing_package.to_dict()

    # We remove `purl` from `existing_mapping` because we use the other purl
    # fields (type, namespace, name, version, etc.) to generate the purl.
    existing_mapping.pop("purl")

    # FIXME REMOVE this workaround when a ScanCode bug fixed with
    # https://github.com/aboutcode-org/scancode-toolkit/commit/9b687e6f9bbb695a10030a81be7b93c8b1d816c2
    qualifiers = new_package_data.get("qualifiers")
    if isinstance(qualifiers, dict):
        # somehow we get an dict on the new value instead of a string
        # this not likely the best place to fix this
        new_package_data["qualifiers"] = normalize_qualifiers(qualifiers, encode=True)

    new_mapping = new_package_data

    fields_to_skip = (
        "package_uid",
        "declared_license_expression_spdx",
        "other_license_expression_spdx",
    )
    updated_fields = []

    for existing_field, existing_value in existing_mapping.items():
        new_value = new_mapping.get(existing_field)
        if TRACE:
            logger.debug(
                "\n".join(
                    [
                        "existing_field:",
                        repr(existing_field),
                        "    existing_value:",
                        repr(existing_value),
                        "    new_value:",
                        repr(new_value),
                    ]
                )
            )

        # FIXME: handle Booleans??? though there are none for now

        # If the checksum from `new_package` is different than the one
        # existing checksum in `existing_package`, there is a big data
        # inconsistency issue and an Exception is raised
        if (
            existing_field in ("md5", "sha1", "sha256", "sha512")
            and existing_value
            and new_value
            and existing_value != new_value
        ):
            raise Exception(
                "\n".join(
                    [
                        f"Mismatched {existing_field} for {existing_package.uri}:",
                        f"    existing_value: {existing_value}",
                        f"    new_value: {new_value}",
                    ]
                )
            )

        if not new_value:
            if TRACE:
                logger.debug("  No new value: skipping")
            continue

        if not existing_value or replace:
            if TRACE and not existing_value:
                logger.debug(f"  No existing value: set to new: {new_value}")

            if TRACE and replace:
                logger.debug(f"  Existing value and replace: set to new: {new_value}")

            if existing_field == "parties":
                # If `existing_field` is `parties`, then we update the `Party` table
                parties = new_value
                existing_parties = Party.objects.filter(package=existing_package)
                serialized_existing_parties = PartySerializer(
                    existing_parties, many=True
                ).data
                if replace:
                    # Delete existing Party objects
                    existing_parties.delete()
                for party in parties:
                    _party, _created = Party.objects.get_or_create(
                        package=existing_package,
                        type=party["type"],
                        role=party["role"],
                        name=party["name"],
                        email=party["email"],
                        url=party["url"],
                    )
                entry = dict(
                    field=existing_field,
                    old_value=serialized_existing_parties,
                    new_value=parties,
                )
                updated_fields.append(entry)
                continue
            elif existing_field == "dependencies":
                # If `existing_field` is `dependencies`, then we update the `DependentPackage` table
                dependencies = new_value
                existing_dependencies = DependentPackage.objects.filter(
                    package=existing_package
                )
                serialized_existing_dependencies = DependentPackageSerializer(
                    existing_dependencies, many=True
                ).data
                if replace:
                    # Delete existing DependentPackage objects
                    existing_dependencies.delete()
                for dependency in dependencies:
                    _dep, _created = DependentPackage.objects.get_or_create(
                        package=existing_package,
                        purl=dependency["purl"],
                        extracted_requirement=dependency["extracted_requirement"],
                        scope=dependency["scope"],
                        is_runtime=dependency["is_runtime"],
                        is_optional=dependency["is_optional"],
                        is_resolved=dependency["is_resolved"],
                    )
                entry = dict(
                    field=existing_field,
                    old_value=serialized_existing_dependencies,
                    new_value=dependencies,
                )
                updated_fields.append(entry)
                continue
            elif existing_field == "package_content":
                # get new_value from extra_data
                new_value = new_mapping.extra_data.get("package_content")
                if not new_value:
                    continue
            elif existing_field in fields_to_skip:
                # Continue to next field
                continue

            # If `existing_field` is not `parties` or `dependencies`, then the
            # `existing_field` is a regular field on the Package model and can
            # be updated normally.
            entry = dict(
                field=existing_field, old_value=existing_value, new_value=new_value
            )
            updated_fields.append(entry)
            setattr(existing_package, existing_field, new_value)
            existing_package.last_modified_date = timezone.now()
            existing_package.save()

        if TRACE:
            logger.debug("  Nothing done")

    return updated_fields


def merge_or_create_package(scanned_package, visit_level, override=False):
    """
    Update Package from ``scanned_package`` instance if `visit_level` is greater
    than the mining level of the existing package.

    If ``scanned_package`` does not exist in the PackageDB, create a new entry in
    the PackageDB for ``scanned_package``.

    If ``override`` is True, then all existing empty values of the PackageDB package are replaced by
    a non-empty value of the provided override.
    """
    created = False
    merged = False
    package = None
    map_error = ""

    mining_level = visit_level
    if override:
        # this will force the data override
        visit_level = +1

    if not isinstance(scanned_package, PackageData):
        msg = "Not a ScanCode PackageData type:" + repr(scanned_package)
        map_error += msg + "\n"
        logger.error(msg)
        raise RuntimeError(msg)

    if not scanned_package.download_url:
        # TODO: there could be valid cases where we have no download URL
        # and still want to create a package???
        msg = "No download_url for package:" + repr(scanned_package)
        map_error += msg + "\n"
        logger.error(msg)
        return package, created, merged, map_error

    package_uri = scanned_package.download_url
    logger.debug(f"Package URI: {package_uri}")
    history = scanned_package.extra_data.get("history", [])

    stored_package = None
    # Check if we already have an existing PackageDB record to update
    # TODO: for now this is done using the package_uri only and
    # we need to refine this to also (or only) use the package_url
    try:
        # FIXME: also consider the Package URL fields!!!
        stored_package = Package.objects.get(download_url=package_uri)
    except Package.DoesNotExist:
        pass

    if stored_package:
        # Here we have a pre-existing package that we are updating.
        # Based on the mining levels, we replace or merge fields
        # differently

        existing_level = stored_package.mining_level

        if visit_level < existing_level:
            # if the level of the new visit is lower than the level
            # of the current package, then existing package data
            # wins and is more important. Its attributes can only be
            # updated if there was a null values and there is a non-
            # null values in the new package data from the visit.
            updated_fields = merge_packages(
                existing_package=stored_package,
                new_package_data=scanned_package.to_dict(),
                replace=False,
            )
            # for a foreign key, such as dependencies and parties, we will adopt the
            # same logic. In this case, parties or dependencies coming from a scanned
            # package are only added if there is no parties or dependencies in the
            # existing stored package
        else:
            # if the level of the new visit is higher or equal to
            # the level of the existing package, then new package
            # data from the visit is more important and wins and its
            # non-null values replace the values of the existing
            # package which is updated in the DB.
            updated_fields = merge_packages(
                existing_package=stored_package,
                new_package_data=scanned_package.to_dict(),
                replace=True,
            )
            # for a foreign key, such as dependencies and parties, we will adopt the
            # same logic. In this case, parties or dependencies coming from a scanned
            # package will override existing values. If there are parties in the scanned
            # package and the existing package, the existing package parties should be
            # deleted first and then the new package's parties added.

            stored_package.mining_level = mining_level

        if updated_fields:
            data = {
                "updated_fields": updated_fields,
            }
            stored_package.append_to_history(
                "Package field values have been updated.", data=data
            )

        # TODO: append updated_fields information to the package's history

        stored_package.last_modified_date = timezone.now()
        stored_package.save()
        logger.debug(f" + Updated package\t: {package_uri}")
        package = stored_package
        merged = True

    else:
        # Here a pre-existing packagedb record does not exist
        # We create a new one from scratch

        # Check to see if we have a package with the same purl, so we can use
        # that package_set value
        # TODO: Consider adding this logic to the Package queryset manager
        existing_related_packages = Package.objects.filter(
            type=scanned_package.type,
            namespace=scanned_package.namespace,
            name=scanned_package.name,
            version=scanned_package.version,
        )
        existing_related_package = existing_related_packages.first()
        package_content = scanned_package.extra_data.get("package_content")

        package_data = dict(
            # FIXME: we should get the file_name in the
            # PackageData object instead.
            filename=fileutils.file_name(package_uri),
            # TODO: update the PackageDB model
            release_date=scanned_package.release_date,
            mining_level=mining_level,
            type=scanned_package.type,
            namespace=scanned_package.namespace,
            name=scanned_package.name,
            version=scanned_package.version,
            qualifiers=normalize_qualifiers(scanned_package.qualifiers, encode=True),
            subpath=scanned_package.subpath,
            primary_language=scanned_package.primary_language,
            description=scanned_package.description,
            keywords=scanned_package.keywords,
            homepage_url=scanned_package.homepage_url,
            download_url=scanned_package.download_url,
            size=scanned_package.size,
            sha1=scanned_package.sha1,
            md5=scanned_package.md5,
            sha256=scanned_package.sha256,
            sha512=scanned_package.sha512,
            bug_tracking_url=scanned_package.bug_tracking_url,
            code_view_url=scanned_package.code_view_url,
            vcs_url=scanned_package.vcs_url,
            copyright=scanned_package.copyright,
            holder=scanned_package.holder,
            declared_license_expression=scanned_package.declared_license_expression,
            license_detections=scanned_package.license_detections,
            other_license_expression=scanned_package.other_license_expression,
            other_license_detections=scanned_package.other_license_detections,
            extracted_license_statement=scanned_package.extracted_license_statement,
            notice_text=scanned_package.notice_text,
            source_packages=scanned_package.source_packages,
            package_content=package_content,
        )

        stringify_null_purl_fields(package_data)

        created_package = Package.objects.create(**package_data)
        created_package.append_to_history(
            f"New Package created from URI: {package_uri}"
        )

        # This is used in the case of Maven packages created from the priority queue
        for h in history:
            created_package.append_to_history(h)

        if existing_related_package:
            related_package_sets_count = existing_related_package.package_sets.count()
            if related_package_sets_count == 0 or (
                related_package_sets_count > 0
                and created_package.package_content == PackageContentType.BINARY
            ):
                # Binary packages can only be part of one set
                package_set = PackageSet.objects.create()
                package_set.add_to_package_set(existing_related_package)
                package_set.add_to_package_set(created_package)
            elif (
                related_package_sets_count > 0
                and created_package.package_content != PackageContentType.BINARY
            ):
                for package_set in existing_related_package.package_sets.all():
                    package_set.add_to_package_set(created_package)

        for party in scanned_package.parties:
            Party.objects.create(
                package=created_package,
                type=party.type,
                role=party.role,
                name=party.name,
                email=party.email,
                url=party.url,
            )

        for dependency in scanned_package.dependencies:
            DependentPackage.objects.create(
                package=created_package,
                purl=dependency.purl,
                extracted_requirement=dependency.extracted_requirement,
                scope=dependency.scope,
                is_runtime=dependency.is_runtime,
                is_optional=dependency.is_optional,
                is_resolved=dependency.is_resolved,
            )

        time = timezone.now()
        created_package.created_date = time
        created_package.last_modified_date = time
        created_package.save()
        package = created_package
        created = True
        logger.debug(f" + Inserted package\t: {package_uri}")

    return package, created, merged, map_error


def update_or_create_resource(package, resource_data):
    """
    Create or update the corresponding purldb Resource from `package` using
    `resource_data`.

    Return a 3-tuple of the corresponding purldb Resource of `resource_data`,
    `resource`, as well as booleans representing whether the Resource was
    created or if the Resources scan field data was updated.
    """
    updated = False
    created = False
    resource = None
    path = resource_data.get("path")

    extra_data = copy.deepcopy(resource_data.get("extra_data", {}))
    extra_data.pop("directory_content", None)
    extra_data.pop("directory_structure", None)

    try:
        resource = Resource.objects.get(package=package, path=path)
        updated = True
    except Resource.DoesNotExist:
        resource = Resource(
            package=package,
            path=path,
            is_file=resource_data.get("type") == "file",
            name=resource_data.get("name"),
            extension=resource_data.get("extension"),
            size=resource_data.get("size"),
            md5=resource_data.get("md5"),
            sha1=resource_data.get("sha1"),
            sha256=resource_data.get("sha256"),
            mime_type=resource_data.get("mime_type"),
            file_type=resource_data.get("file_type"),
            programming_language=resource_data.get("programming_language"),
            is_binary=resource_data.get("is_binary"),
            is_text=resource_data.get("is_text"),
            is_archive=resource_data.get("is_archive"),
            is_media=resource_data.get("is_media"),
            is_key_file=resource_data.get("is_key_file"),
            extra_data=extra_data,
        )
        created = True
    _ = resource.set_scan_results(resource_data, save=True)
    resource.update_extra_data(extra_data)
    return resource, created, updated
