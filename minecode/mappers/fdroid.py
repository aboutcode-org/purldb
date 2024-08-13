#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging

from packagedcode.models import PackageData
from packagedcode.models import Party
from packagedcode.models import party_person
from packageurl import PackageURL

from minecode import map_router
from minecode.mappers import Mapper

TRACE = False

logger = logging.getLogger(__name__)

if TRACE:
    import sys

    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


@map_router.route("pkg:fdroid/.+")
class FdroidPackageMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package(s) built from the index data for all versions of an F-Droid
        package, aka. in F-Droid as an "application"
        """
        if resource_uri.data:
            visited_data = json.loads(resource_uri.data)
            yield from build_packages(purl=resource_uri.package_url, data=visited_data)


def build_packages(purl, data):
    """
    Yield PackageData built from ``data`` corresponding to a single package name
    and many package versions for a given ``purl`` string
    """
    metadata = data["metadata"]

    # we map categories to keyword
    # "categories": ["Time"],
    keywords = metadata.get("categories", [])

    # "issueTracker": "https://github.com/jdmonin/anstop/issues",
    bug_tracking_url = metadata.get("issueTracker")

    # "license": "GPL-2.0-only",
    # this is supposed to be an SPDX expression
    extracted_license_statement = metadata.get("license")

    # "sourceCode": "https://github.com/jdmonin/anstop",
    vcs_url = metadata.get("sourceCode")

    # "webSite": "https://sourceforge.net/projects/androidspeedo",
    homepage_url = metadata.get("webSite")

    description = build_description(metadata, language="en-US")

    parties = []
    # "authorEmail": "jigsaw-code@google.com",
    # "authorName": "Jigsaw",
    # "authorWebSite": "https://jigsaw.google.com/",
    author_name = metadata.get("authorName")
    author_email = metadata.get("authorEmail")
    author_url = metadata.get("authorWebSite")
    if any([author_name, author_email, author_url]):
        parties.append(
            Party(
                type=party_person,
                name=author_name,
                role="author",
                email=author_email,
                url=author_url,
            )
        )

    # TODO: add these
    # release_date
    # code_view_url
    # copyright
    #
    # and changelog, sourceCode, donate, translation, antiFeatures

    base_purl = PackageURL.from_string(purl)
    shared_data = dict(
        type=base_purl.type,
        name=base_purl.name,
        keywords=keywords,
        bug_tracking_url=bug_tracking_url,
        extracted_license_statement=extracted_license_statement,
        vcs_url=vcs_url,
        homepage_url=homepage_url,
        repository_homepage_url=f"https://f-droid.org/en/packages/{base_purl.name}",
        description=description,
        parties=parties,
    )

    # "versions": {
    #   "78ec7805f5a49b156fbd5f6af174c1cd8ae9900c9c7af2b2df021aca8cd5eae9": {
    #     "added": 1344556800000,
    #     "file": {
    #           "name": "/An.stop_10.apk", ....
    versions = data["versions"]

    for _sha256_of_apk, version_data in versions.items():
        # TODO: collect versionName
        version_code = str(version_data["manifest"]["versionCode"])
        logger.debug(f"build_packages: base_purl: {base_purl} version: {version_code}")
        logger.debug(f"build_packages: data: {version_data}")

        # TODO: add  release_date from "added": 1655164800000,

        # these must exists since F-Droid builds from sources
        src = version_data["src"]
        src_filename = src["name"]
        src_sha256 = src["sha256"]
        src_size = src["size"]
        download_url = f'https://f-droid.org/repo/{src_filename.strip("/")}'

        package_mapping = dict(
            version=version_code,
            download_url=download_url,
            repository_download_url=download_url,
            sha256=src_sha256,
            size=src_size,
        )
        package_mapping.update(shared_data)
        src = PackageData.from_data(package_mapping)
        yield src

        source_package = PackageURL(
            type=src.type,
            name=src.name,
            version=src.version,
            qualifiers=dict(download_url=download_url),
        )

        # these must exists or there is no F-Droid package
        file = version_data["file"]
        filename = file["name"]
        sha256 = file["sha256"]
        size = file["size"]
        download_url = f"https://f-droid.org/repo/{filename}"

        package_mapping = dict(
            version=version_code,
            download_url=download_url,
            repository_download_url=download_url,
            sha256=sha256,
            size=size,
            source_packages=[source_package.to_string()],
        )
        package_mapping.update(shared_data)
        yield PackageData.from_data(package_mapping)


def build_description(metadata, language="en-US"):
    r"""
    Return a description in ``language`` built from
    a package name, summary and description, one per line.
    Skip redundant or empty parts.

    For example::

    >>> metadata = {
    ...   "name": {"en-US": "Anstop"},
    ...   "summary": {"en-US": "A simple stopwatch"},
    ...   "description": {"en-US": "A really simple stopwatch"}
    ... }
    >>> build_description(metadata)
    'Anstop\nA simple stopwatch\nA really simple stopwatch'

    >>> metadata = {
    ...   "name": {"en-US": "Anstop"},
    ...   "summary": {"en-US": "Anstop A simple stopwatch"},
    ...   "description": {"en-US": "Anstop A simple stopwatch, nice and sweet."}
    ... }
    >>> build_description(metadata)
    'Anstop A simple stopwatch, nice and sweet.'

    >>> metadata = {
    ...   "name": {"en-US": "Anstop"},
    ...   "summary": {"dutch": "Anstop A simple stopwatch"},
    ...   "description": {"dutch": "Anstop A simple stopwatch, nice and sweet."}
    ... }
    >>> build_description(metadata)
    'Anstop'
    """
    names = metadata.get("name") or {}
    name = names.get(language)

    summaries = metadata.get("summary") or {}
    summary = summaries.get(language)

    if name and summary and summary.startswith(name):
        name = None

    descriptions = metadata.get("description") or {}
    description = descriptions.get(language)

    if summary and description and description.startswith(summary):
        summary = None

    non_empty_parts = [p for p in [name, summary, description] if p]
    return "\n".join(non_empty_parts)
