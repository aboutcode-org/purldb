#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import gzip
import json
import logging
import os

import saneyaml
from packagedcode import models as scan_models
from packagedcode.models import DependentPackage
from packagedcode.models import PackageData
from packageurl import PackageURL
from rubymarshal import reader
from rubymarshal.classes import UsrMarshal

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import Mapper
from minecode.miners import NonPersistentHttpVisitor
from minecode.utils import extract_file
from minecode.utils import parse_date

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# FIXME: we are missing several API calls:
# http://guides.rubygems.org/rubygems-org-api/


class RubyGemsSeed(seed.Seeder):
    def get_seeds(self):
        # We keep only specs.4.8.gz and exclude latest_spec.4.8.gz,
        # since specs.4.8.gz covers all uris in latest spec.
        yield "http://rubygems.org/specs.4.8.gz"


class GemVersion(UsrMarshal):
    def version(self):
        return self.values["version"]


@visit_router.route(r"https?://rubygems\.org/specs\.4\.8\.gz")
class RubyGemsIndexVisitor(NonPersistentHttpVisitor):
    """Collect REST APIs URIs from RubyGems index file."""

    def get_uris(self, content):
        with gzip.open(content, "rb") as idx:
            index = idx.read()

        # TODO: use a purl!!!
        for name, version, platform in reader.loads(index):
            json_url = "https://rubygems.org/api/v1/versions/{name}.json".format(
                **locals()
            )

            package_url = PackageURL(type="gem", name=name).to_string()
            yield URI(uri=json_url, package_url=package_url, source_uri=self.uri)

            # note: this list only has ever a single value
            version = version.values[0]
            if isinstance(version, bytes):
                version = version.decode("utf-8")

            download_url = "https://rubygems.org/downloads/{name}-{version}"

            if isinstance(platform, bytes):
                platform = platform.decode("utf-8")
            if platform != "ruby":
                download_url += "-{platform}"

            download_url += ".gem"
            download_url = download_url.format(**locals())
            package_url = PackageURL(type="gem", name=name, version=version).to_string()
            yield URI(uri=download_url, package_url=package_url, source_uri=self.uri)


@visit_router.route(r"https?://rubygems\.org/api/v1/versions/[\w\-\.]+.json")
class RubyGemsApiManyVersionsVisitor(HttpJsonVisitor):
    """
    Collect the json content of each version.
    Yield the uri of each gem based on name, platform and version.
    The data of the uri is the JSON subset for a single version.
    """

    def get_uris(self, content):
        """Yield URI of the gems url and data."""
        # FIXME: return actual data too!!!
        for version_details in content:
            # get the gems name by parsing from the uri
            name = self.uri[
                self.uri.index("/versions/") + len("/versions/") : -len(".json")
            ]
            version = version_details.get("number")
            gem_name = f"{name}-{version}"
            package_url = PackageURL(type="gem", name=name, version=version).to_string()
            download_url = f"https://rubygems.org/downloads/{gem_name}.gem"
            yield URI(
                uri=download_url,
                source_uri=self.uri,
                package_url=package_url,
                data=json.dumps(version_details),
            )


# TODO: add API dependencies
# https://rubygems.org/api/v1/dependencies.json?gems=file_validators
# Also use Use the V2 API at http://guides.rubygems.org/rubygems-org-api-v2/
# GET - /api/v2/rubygems/[GEM NAME]/versions/[VERSION NUMBER].(json|yaml)


@visit_router.route(r"https?://rubygems.org/downloads/[\w\-\.]+.gem")
class RubyGemsPackageArchiveMetadataVisitor(NonPersistentHttpVisitor):
    """Fetch a Rubygems gem archive, extract it and return its metadata file content."""

    def dumps(self, content):
        return get_gem_metadata(content)


def get_gem_metadata(location):
    """
    Return the metadata file content as a string extracted from the gem archive
    at `location`.
    """
    # Extract the compressed file first.
    extracted_location = extract_file(location)
    metadata_gz = os.path.join(extracted_location, "metadata.gz")
    # Extract the embedded metadata gz file
    extract_parent_location = extract_file(metadata_gz)
    # Get the first file in the etracted folder which is the meta file location
    meta_extracted_file = os.path.join(
        extract_parent_location, os.listdir(extract_parent_location)[0]
    )
    with open(meta_extracted_file) as meta_file:
        return meta_file.read()


@map_router.route(r"https*://rubygems\.org/api/v1/versions/[\w\-\.]+.json")
class RubyGemsApiVersionsJsonMapper(Mapper):
    """Mapper to build Rubygems Packages from JSON API data."""

    def get_packages(self, uri, resource_uri):
        metadata = json.loads(resource_uri.data)
        _, sep, namejson = uri.partition("versions/")
        if not sep:
            return
        name, sep, _ = namejson.rpartition(".json")
        if not sep:
            return
        return build_rubygem_packages_from_api_data(metadata, name)


def build_rubygem_packages_from_api_data(metadata, name, purl=None):
    """
    Yield Package built from resource_uri record for a single
    package version.
    metadata: json metadata content
    name: package name
    purl: String value of the package url of the ResourceURI object
    """
    for version_details in metadata:
        short_desc = version_details.get("summary")
        long_desc = version_details.get("description")
        if long_desc == short_desc:
            long_desc = None
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = "\n".join(descriptions)
        package = dict(
            type="gem",
            name=name,
            description=description,
            version=version_details.get("number"),
        )
        # FIXME: we are missing deps and more things such as download URL and more

        if version_details.get("sha"):
            package["sha256"] = version_details.get("sha")

        package["release_date"] = (
            parse_date(version_details.get("created_at") or "") or None
        )

        author = version_details.get("authors")
        if author:
            parties = package.get("parties")
            if not parties:
                package["parties"] = []
            party = scan_models.Party(name=author, role="author")
            package["parties"].append(party)

        extracted_license_statement = []
        licenses = version_details.get("licenses")
        if licenses:
            for lic in licenses:
                extracted_license_statement.append(lic)
        if extracted_license_statement:
            package["extracted_license_statement"] = extracted_license_statement
        package = PackageData.from_data(package)
        package.set_purl(purl)
        yield package


def build_rubygem_packages_from_api_v2_data(metadata_dict, purl):
    """
    Yield ScannedPackage built from RubyGems API v2.
    purl: String value of the package url of the ResourceURI object
    """
    name = metadata_dict["name"]
    version = metadata_dict["version"]
    description = metadata_dict["description"]
    homepage_url = metadata_dict["homepage_uri"]
    repository_homepage_url = metadata_dict["project_uri"]
    release_date = metadata_dict["version_created_at"]

    extracted_license_statement = []
    lic_list = metadata_dict["licenses"]
    if lic_list:
        extracted_license_statement = lic_list

    # mapping of information that are common to all the downloads of a
    # version
    common_data = dict(
        name=name,
        version=version,
        description=description,
        homepage_url=homepage_url,
        repository_homepage_url=repository_homepage_url,
        release_date=release_date,
        extracted_license_statement=extracted_license_statement,
    )

    author = metadata_dict["authors"]
    if author:
        parties = common_data.get("parties")
        if not parties:
            common_data["parties"] = []
        common_data["parties"].append(scan_models.Party(name=author, role="author"))

    download_url = metadata_dict["gem_uri"]

    download_data = dict(
        datasource_id="gem_pkginfo",
        type="gem",
        download_url=download_url,
        sha256=metadata_dict["sha"],
    )
    download_data.update(common_data)
    package = scan_models.PackageData.from_data(download_data)

    package.datasource_id = "gem_api_metadata"
    package.set_purl(purl)
    yield package


@map_router.route(r"https?://rubygems.org/downloads/[\w\-\.]+.gem")
class RubyGemsPackageArchiveMetadataMapper(Mapper):
    """Mapper to build on e Package from the metadata file found inside a gem."""

    def get_packages(self, uri, resource_uri):
        metadata = resource_uri.data
        return build_rubygem_packages_from_metadata(metadata, download_url=uri)


def build_rubygem_packages_from_metadata(metadata, download_url=None, purl=None):
    """
    Yield Package built from a Gem `metadata` YAML content
    metadata: json metadata content
    download_url: url to download the package
    purl: String value of the package url of the ResourceURI object
    """
    content = saneyaml.load(metadata)
    if not content:
        return

    name = content.get("name")
    short_desc = content.get("summary")
    long_desc = content.get("description")
    if long_desc == short_desc:
        long_desc = None
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = "\n".join(descriptions)
    package = dict(
        type="gem",
        name=name,
        description=description,
        homepage_url=content.get("homepage"),
    )
    if download_url:
        package["download_url"] = download_url

    extracted_license_statement = []
    licenses = content.get("licenses")
    if licenses:
        for lic in licenses:
            extracted_license_statement.append(lic)
    if extracted_license_statement:
        package["extracted_license_statement"] = extracted_license_statement

    authors = content.get("authors")
    for author in authors:
        parties = package.get("parties")
        if not parties:
            package["parties"] = []
        party = scan_models.Party(name=author, role="author")
        package["parties"].append(party)

    # Release date in the form of `2010-02-01 00:00:00 -05:00`
    release_date = content.get("date", "").split()
    package["release_date"] = parse_date(release_date[0])

    package["dependencies"] = get_dependencies_from_meta(content) or []

    # This is a two level nenest item
    version1 = content.get("version") or {}
    version = version1.get("version") or None
    package["version"] = version
    package = PackageData.from_data(package)
    package.set_purl(purl)
    yield package


def get_dependencies_from_meta(content):
    """
    Return a mapping of dependencies keyed by group based on the gem YAML
    metadata data structure.
    """
    dependencies = content.get("dependencies") or []
    if not dependencies:
        return []

    group = []
    for dependency in dependencies:
        name = dependency.get("name") or None
        if not name:
            continue

        requirement = dependency.get("requirement") or {}
        # FIXME when upating to the ScanCode package model
        scope = dependency.get("type")
        scope = scope and scope.lstrip(":")

        # note that as weird artifact of our saneyaml YAML parsing, we are
        # getting both identical requirements and version_requirements mapping.
        # We ignore version_requirements
        # requirement is {'requirements': [
        #                     [u'>=', {'version': '0'}]
        #                   ]
        #                }
        requirements = requirement.get("requirements") or []
        version_constraint = []

        # each requirement is [u'>=', {'version': '0'}]
        for constraint, req_version in requirements:
            req_version = req_version.get("version") or None
            # >= 0 allows for any version: we ignore these type of contrainsts
            # as this is the same as no constraints. We also ignore lack of
            # constraints and versions
            if (constraint == ">=" and req_version == "0") or not (
                constraint and req_version
            ):
                continue
            version_constraint.append(" ".join([constraint, req_version]))
        version_constraint = ", ".join(version_constraint) or None

        group.append(
            DependentPackage(
                purl=name, extracted_requirement=version_constraint, scope=scope
            )
        )

    return group


def get_dependencies_from_api(content):
    """
    Return a mapping of dependencies keyed by group based on the RubyGems API
    data structure.
    """
    dependencies = content.get("dependencies") or []
    if not dependencies:
        return {}

    group = []
    for dependency in dependencies:
        name = dependency.get("name") or None
        if not name:
            continue

        requirement = dependency.get("requirement") or {}
        scope = dependency.get("type")
        scope = scope and scope.lstrip(":")

        # note that as weird artifact of our saneyaml YAML parsing, we are
        # getting both identical requirements and version_requirements mapping.
        # We ignore version_requirements
        # requirement is {'requirements': [
        #                     [u'>=', {'version': '0'}]
        #                   ]
        #                }
        requirements = requirement.get("requirements") or []
        version_constraint = []
        # each requirement is [u'>=', {'version': '0'}]
        for constraint, req_version in requirements:
            req_version = req_version.get("version") or None
            # >= 0 allows for any version: we ignore these type of contrainsts
            # as this is the same as no constraints. We also ignore lack of
            # constraints and versions
            if (constraint == ">=" and req_version == "0") or not (
                constraint and req_version
            ):
                continue
            version_constraint.append(" ".join([constraint, req_version]))
        version_constraint = ", ".join(version_constraint) or None

        group.append(
            DependentPackage(
                purl=name, extracted_requirement=version_constraint, scope=scope
            )
        )

    return group


# Structure: {gem_spec: license.key}
LICENSES_MAPPING = {
    "None": None,
    "Apache 2.0": "apache-2.0",
    "Apache License 2.0": "apache-2.0",
    "Apache-2.0": "apache-2.0",
    "Apache": "apache-2.0",
    "GPL": "gpl-2.0",
    "GPL-2": "gpl-2.0",
    "GNU GPL v2": "gpl-2.0",
    "GPLv2+": "gpl-2.0-plus",
    "GPLv2": "gpl-2.0",
    "GPLv3": "gpl-3.0",
    "MIT": "mit",
    "Ruby": "ruby",
    "same as ruby's": "ruby",
    "Ruby 1.8": "ruby",
    "Artistic 2.0": "artistic-2.0",
    "Perl Artistic v2": "artistic-2.0",
    "2-clause BSDL": "bsd-simplified",
    "BSD": "bsd-new",
    "BSD-3": "bsd-new",
    "ISC": "isc",
    "SIL Open Font License": "ofl-1.0",
    "New Relic": "new-relic",
    "GPL2": "gpl-2.0",
    "BSD-2-Clause": "bsd-simplified",
    "BSD 2-Clause": "bsd-simplified",
    "LGPL-3": "lgpl-3.0",
    "LGPL-2.1+": "lgpl-2.1-plus",
    "LGPLv2.1+": "lgpl-2.1-plus",
    "LGPL": "lgpl",
    "Unlicense": "unlicense",
}
