from uuid import uuid4
import logging
import sys

from minecode.models import ScannableURI
from commoncode import fileutils
from packageurl import normalize_qualifiers

from packagedb.models import Package
from packagedb.models import Party
from packagedb.models import DependentPackage
from packagedcode.models import PackageData
from minecode.utils import stringify_null_purl_fields
from django.utils import timezone

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


def add_package_to_scan_queue(package):
    """
    Add a Package `package` to the scan queue
    """
    uri = package.download_url
    _, scannable_uri_created = ScannableURI.objects.get_or_create(
        uri=uri,
        package=package,
    )
    if scannable_uri_created:
        logger.debug(' + Inserted ScannableURI\t: {}'.format(uri))


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
    existing_mapping.pop('purl')

    # FIXME REMOVE this workaround when a ScanCode bug fixed with
    # https://github.com/nexB/scancode-toolkit/commit/9b687e6f9bbb695a10030a81be7b93c8b1d816c2
    qualifiers = new_package_data.get('qualifiers')
    if isinstance(qualifiers, dict):
        # somehow we get an dict on the new value instead of a string
        # this not likely the best place to fix this
        new_package_data['qualifiers'] = normalize_qualifiers(qualifiers, encode=True)

    new_mapping = new_package_data

    fields_to_skip = ('package_uid',)

    for existing_field, existing_value in existing_mapping.items():
        new_value = new_mapping.get(existing_field)
        if TRACE:
            logger.debug(
                '\n'.join([
                    'existing_field:', repr(existing_field),
                    '    existing_value:', repr(existing_value),
                    '    new_value:', repr(new_value)])
            )

        # FIXME: handle Booleans??? though there are none for now

        # If the checksum from `new_package` is different than the one
        # existing checksum in `existing_package`, there is a big data
        # inconsistency issue and an Exception is raised
        if (existing_field in ('md5', 'sha1', 'sha256', 'sha512') and
                existing_value and
                new_value and
                existing_value != new_value):
            raise Exception(
                '\n'.join([
                    'Mismatched {} for {}:'.format(existing_field, existing_package.uri),
                    '    existing_value: {}'.format(existing_value),
                    '    new_value: {}'.format(new_value)
                ])
            )

        if not new_value:
            if TRACE:
                logger.debug('  No new value: skipping')
            continue

        if not existing_value or replace:
            if TRACE and not existing_value:
                logger.debug(
                    '  No existing value: set to new: {}'.format(new_value))

            if TRACE and replace:
                logger.debug(
                    '  Existing value and replace: set to new: {}'.format(new_value))

            if existing_field == 'parties':
                # If `existing_field` is `parties`, then we update the `Party` table
                parties = new_value
                if replace:
                    # Delete existing Party objects
                    Party.objects.filter(package=existing_package).delete()
                for party in parties:
                    _party, _created = Party.objects.get_or_create(
                        package=existing_package,
                        type=party['type'],
                        role=party['role'],
                        name=party['name'],
                        email=party['email'],
                        url=party['url'],
                    )
            elif existing_field == 'dependencies':
                # If `existing_field` is `dependencies`, then we update the `DependentPackage` table
                dependencies = new_value
                if replace:
                    # Delete existing DependentPackage objects
                    DependentPackage.objects.filter(package=existing_package).delete()
                for dependency in dependencies:
                    _dep, _created = DependentPackage.objects.get_or_create(
                        package=existing_package,
                        purl=dependency['purl'],
                        extracted_requirement=dependency['extracted_requirement'],
                        scope=dependency['scope'],
                        is_runtime=dependency['is_runtime'],
                        is_optional=dependency['is_optional'],
                        is_resolved=dependency['is_resolved'],
                    )
            elif existing_field in fields_to_skip:
                # Continue to next field
                continue
            else:
                # If `existing_field` is not `parties` or `dependencies`, then the
                # `existing_field` is a regular field on the Package model and can
                # be updated normally.
                setattr(existing_package, existing_field, new_value)
                existing_package.save()

        if TRACE:
            logger.debug('  Nothing done')


def merge_or_create_package(scanned_package, visit_level):
    """
    Update Package from `scanned_package` instance if `visit_level` is greater
    than the mining level of the existing package.

    If `scanned_package` does not exist in the PackageDB, create a new entry in
    the PackageDB for `scanned_package`.
    """
    created = False
    merged = False
    package = None
    map_error = ''

    if not isinstance(scanned_package, PackageData):
        msg = 'Not a ScanCode PackageData type:' + repr(scanned_package)
        map_error += msg + '\n'
        logger.error(msg)
        raise RuntimeError(msg)

    if not scanned_package.download_url:
        # TODO: there could be valid cases where we have no download URL
        # and still want to create a package???
        msg = 'No download_url for package:' + repr(scanned_package)
        map_error += msg + '\n'
        logger.error(msg)
        return package, created, merged, map_error

    package_uri = scanned_package.download_url
    logger.debug('Package URI: {}'.format(package_uri))
    history = scanned_package.extra_data.get('history', [])

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
            merge_packages(
                existing_package=stored_package,
                new_package_data=scanned_package.to_dict(),
                replace=False)
            stored_package.append_to_history('Existing Package values retained due to ResourceURI mining level via map_uri().')
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
            merge_packages(
                existing_package=stored_package,
                new_package_data=scanned_package.to_dict(),
                replace=True)
            stored_package.append_to_history('Existing Package values replaced due to ResourceURI mining level via map_uri().')
            # for a foreign key, such as dependencies and parties, we will adopt the
            # same logic. In this case, parties or dependencies coming from a scanned
            # package will override existing values. If there are parties in the scanned
            # package and the existing package, the existing package parties should be
            # deleted first and then the new package's parties added.

            stored_package.mining_level = visit_level

        stored_package.last_modified_date = timezone.now()
        stored_package.save()
        logger.debug(' + Updated package\t: {}'.format(package_uri))
        package = stored_package
        merged = True

    else:
        # Here a pre-existing packagedb record does not exist
        # We create a new one from scratch

        # Check to see if we have a package with the same purl, so we can use
        # that package_set value
        # TODO: Consider adding this logic to the Package queryset manager
        p = Package.objects.filter(
            type=scanned_package.type,
            namespace=scanned_package.namespace,
            name=scanned_package.name,
            version=scanned_package.version,
        ).first()
        if p and p.package_set:
            package_set = p.package_set
        else:
            package_set = uuid4()

        package_data = dict(
            # FIXME: we should get the file_name in the
            # PackageData object instead.
            filename=fileutils.file_name(package_uri),
            # TODO: update the PackageDB model
            release_date=scanned_package.release_date,
            mining_level=visit_level,
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
            declared_license_expression_spdx=scanned_package.declared_license_expression_spdx,
            license_detections=scanned_package.license_detections,
            other_license_expression=scanned_package.other_license_expression,
            other_license_expression_spdx=scanned_package.other_license_expression_spdx,
            other_license_detections=scanned_package.other_license_detections,
            extracted_license_statement=scanned_package.extracted_license_statement,
            notice_text=scanned_package.notice_text,
            source_packages=scanned_package.source_packages,
            package_set=package_set,
        )

        stringify_null_purl_fields(package_data)

        created_package = Package.objects.create(**package_data)
        created_package.append_to_history('New Package created from ResourceURI: {} via map_uri().'.format(package_uri))

        # This is used in the case of Maven packages created from the priority queue
        for h in history:
            created_package.append_to_history(h)

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

        created_package.last_modified_date = timezone.now()
        created_package.save()
        package = created_package
        created = True
        logger.debug(' + Inserted package\t: {}'.format(package_uri))

    return package, created, merged, map_error
