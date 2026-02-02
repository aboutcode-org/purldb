#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import signal
import sys
import time

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.utils import OperationalError
from django.utils import timezone

from packagedcode import licensing
from packagedcode import maven
from packagedcode import npm
from packagedcode import nuget
from packagedcode import pypi
from packagedcode import rubygems
from packagedcode.models import Package as ScannedPackage

from clearcode.models import CDitem
from clearindex import harvest
from minecode.management.commands import VerboseCommand
from minecode.management.commands import get_error_message
from minecode.model_utils import merge_packages
from minecode.utils import stringify_null_purl_fields
from packagedb.models import Package

TRACE = False

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 10

MUST_STOP = False


def stop_handler(*args, **kwargs):
    """Signal handler to set global variable to True."""
    global MUST_STOP
    MUST_STOP = True


signal.signal(signal.SIGTERM, stop_handler)

# number of mappable CDItem processed at once
MAP_BATCH_SIZE = 10


PACKAGE_TYPES_BY_CD_TYPE = {
    "crate": "cargo",
    "deb": "deb",
    "debsrc": "deb",
    # Currently used only for maven packages
    "sourcearchive": "maven",
    "maven": "maven",
    "composer": "composer",
    # Currently used only for Github repo/packages
    "git": "github",
    "pod": "pod",
    "nuget": "nuget",
    "pypi": "pypi",
    "gem": "gem",
}


# TODO: Update with more Package types when scancode-toolkit is updated
PACKAGE_TYPES_WITH_GET_URLS = {
    "maven": maven.get_urls,
    "npm": npm.get_urls,
    "pypi": pypi.get_pypi_urls,
    "gem": rubygems.get_urls,
    "nuget": nuget.get_urls,
}


class Command(VerboseCommand):
    help = "Run a mapping worker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--exit-on-empty",
            dest="exit_on_empty",
            default=False,
            action="store_true",
            help="Do not loop forever. Exit when the queue is empty.",
        )

    def handle(self, *args, **options):
        """
        Get the next available CDitem and start the processing.
        Loops forever and sleeps a short while if there are no CDitem left to map.
        """
        global MUST_STOP

        logger.setLevel(self.get_verbosity(**options))
        exit_on_empty = options.get("exit_on_empty")

        sleeping = False
        created_packages_count = 0

        logger.info("Running ClearIndex")
        while True:
            if MUST_STOP:
                logger.info("Graceful exit of the map loop.")
                break

            mappable_definitions = CDitem.objects.mappable_definitions()[:MAP_BATCH_SIZE]
            mappable_scancode_harvests = CDitem.objects.mappable_scancode_harvests()[
                :MAP_BATCH_SIZE
            ]

            try:
                if not mappable_definitions and not mappable_scancode_harvests:
                    if exit_on_empty:
                        logger.info("No mappable CDitem, exiting...")
                        break

                    # Only log a single message when we go to sleep
                    if not sleeping:
                        sleeping = True
                        logger.info("No mappable CDitem, sleeping...")

                    time.sleep(SLEEP_WHEN_EMPTY)
                    continue

                sleeping = False

                for cditem in mappable_definitions:
                    package = map_definition(cditem)
                    if not package:
                        continue
                    created_packages_count += 1

                for cditem in mappable_scancode_harvests:
                    # scancode harvests may contain multiple package entries
                    package_count = harvest.map_scancode_harvest(cditem)
                    if isinstance(package_count, int):
                        created_packages_count += package_count

            except OperationalError as e:
                logger.error(e)
                break

            msg = "{}: {} Packages processed."
            msg = msg.format(timezone.now(), created_packages_count)
            logger.info(msg)


def map_definition(cditem):
    """
    Map a CD definition. Return the Package created from a mapped CD definition
    or None if a Package could not be created or an Exception has occurred.
    """
    try:
        with transaction.atomic():
            # We create a new Package from a definition, if it does not exist in the PackageDB
            package = get_or_create_package_from_cditem_definition(cditem)
            if not package:
                return
            package.last_modified_date = timezone.now()
            package.save()
            cditem.last_map_date = timezone.now()
            cditem.save()
            return package
    except Exception as e:
        msg = f"Error: Failed to map while processing CDitem: {repr(cditem.path)}\n"
        msg += get_error_message(e)
        logger.error(msg)
        cditem.map_error = msg
        cditem.save()


def get_coords_des_and_lic_from_def(definition):
    return (
        definition.get("coordinates", {}),
        definition.get("described", {}),
        definition.get("licensed", {}),
    )


# CD_TYPES_WITH_SOURCE = ('debsrc', 'npm', 'sourcearchive',)


def get_or_create_package_from_cditem_definition(cditem):
    """Create a Package from a CDitem definition or return a Package if it already exists"""
    definition = cditem.data
    if not definition:
        raise Exception("No data available for this definition")
    coordinates, described, licensed = get_coords_des_and_lic_from_def(definition)

    download_url = described.get("urls", {}).get("download", "")
    if not download_url:
        # We use our data to create a Package in order to form the download_url, since we do not have the download_url for the Package
        # We need to have a unique download URL for every Package
        download_url = create_download_url_from_coords(coordinates)
        if not download_url:
            raise Exception("No download URL is available for this definition")

    if download_url.startswith("http://central.maven.org"):
        split_download_url = download_url.rsplit("http://central.maven.org")
        if len(split_download_url) == 2:
            download_url = "https://repo1.maven.org" + split_download_url[1]

    stringify_null_purl_fields(coordinates)

    namespace = coordinates.get("namespace")
    namespace = namespace if namespace != "-" else ""
    name = coordinates.get("name")
    version = coordinates.get("revision")
    package_type = coordinates.get("type")
    converted_package_type = PACKAGE_TYPES_BY_CD_TYPE.get(package_type) or package_type
    # TODO: Source packages need to be updated for clearlydefined, link source packages to binary packages
    hashes = described.get("hashes", {})
    sha1 = hashes.get("sha1")
    sha256 = hashes.get("sha256")
    homepage_url = described.get("projectWebsite")
    release_date = described.get("releaseDate")
    declared_license = licensed.get("declared")
    normalized_license_expression = licensing.get_normalized_expression(declared_license)
    copyrights = get_parties_from_licensed(licensed)
    copyrights = "\n".join(copyrights)
    definition_mining_level = 0

    existing_package = None
    try:
        # FIXME: also consider the Package URL fields!!!
        existing_package = Package.objects.get(download_url=download_url)
    except ObjectDoesNotExist:
        pass

    if not existing_package:
        package, created = Package.objects.get_or_create(
            type=converted_package_type,
            namespace=namespace,
            name=name,
            version=version,
            download_url=download_url,
            homepage_url=homepage_url,
            sha1=sha1,
            sha256=sha256,
            release_date=release_date,
            declared_license=declared_license,
            license_expression=normalized_license_expression,
            copyright=copyrights,
            mining_level=definition_mining_level,
        )
        # log history if package was created
        if created:
            package.append_to_history(f"Created package from CDitem definition: {cditem.path}")

    else:
        # TODO: This is temporary until we fold clearindex into minecode mapping
        # proper, otherwise we should base this decision off of mining level
        # if existing_package.mining_level < definition_mining_level:
        new_package_data = ScannedPackage(
            type=converted_package_type,
            namespace=namespace,
            name=name,
            version=version,
            download_url=download_url,
            homepage_url=homepage_url,
            sha1=sha1,
            sha256=sha256,
            release_date=release_date,
            declared_license=declared_license,
            license_expression=normalized_license_expression,
            copyright=copyrights,
        ).to_dict()
        merge_packages(
            existing_package=existing_package,
            new_package_data=new_package_data,
            replace=True,
        )
        package = existing_package
        package.append_to_history(f"Updated package from CDitem definition: {cditem.path}")

    return package


def is_scancode_scan(harvest):
    return harvest.get("_metadata", {}).get("type", "") == "scancode"


def create_download_url_from_coords(coord):
    """Return a download URL for a supported Package from Coordinates `coord`"""
    ptype = coord.get("type")
    namespace = coord.get("namespace")
    name = coord.get("name")
    version = coord.get("revision")

    package_type = PACKAGE_TYPES_BY_CD_TYPE.get(ptype)
    if not package_type:
        raise Exception(f"Unsupported ClearlyDefined package type: {ptype}")

    get_urls = PACKAGE_TYPES_WITH_GET_URLS.get(package_type)
    if get_urls:
        urls = get_urls(namespace=namespace, name=name, version=version)
        return urls["repository_download_url"]


def str2coord(s):
    """
    Return a mapping of CD coordinates from a `s` CD coordinates, URL or URN
    string.

    Some example of the supported input strings are:
        URL: "cd:/gem/rubygems/-/mocha/1.7.0"
        URN: "urn:gem:rubygems:-:mocha:revision:1.7.0:tool:scancode:3.1.0"
        plain: /gem/rubygems/foo/mocha/1.7.0"
    """
    from itertools import izip_longest

    is_urn = s.startswith("urn")
    is_url = s.startswith("cd:")
    splitter = ":" if is_urn else "/"
    segments = s.strip(splitter).split(splitter)
    if is_urn or is_url:
        segments = segments[1:]
    # ignore extra segments for now beyond the 5 first (such as the PR of a curation)
    segments = segments[:5]

    fields = (
        "type",
        "provider",
        "namespace",
        "name",
        "revision",
    )
    return dict(izip_longest(fields, segments))


def get_parties_from_licensed(licensed):
    """Return a list of Copyright statements from `licensed`, if available"""
    return licensed.get("facets", {}).get("core", {}).get("attribution", {}).get("parties", [])
