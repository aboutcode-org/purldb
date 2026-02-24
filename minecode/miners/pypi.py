#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import codecs
import json
import xmlrpc

from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import Mapper
from minecode.miners import Visitor
from minecode.utils import get_temp_file
from minecode.utils import parse_date

"""
Visitors for Pypi and Pypi-like Python package repositories.

We have this hierarchy in Pypi:
    index (xmlrpc) -> packages (json) -> package releases (json) -> download urls

Pypi serves a main index via XMLRPC that contains a list of package names.
For each package, a JSON contains details including the list of all releases.
For each release, a JSON contains details for the released version and all the
downloads available for this release. We create Packages at this level as well
as one download URI for each effective download.

Some information about every release and download is replicated in every JSON
payload and is ignored for simplicity (which is not super efficient).
"""


class PypiSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://pypi.python.org/pypi/"


@visit_router.route("https://pypi.python.org/pypi/")
class PypiIndexVisitor(Visitor):
    """Collect package metadata URIs from the top level pypi index for each package."""

    def fetch(self, uri, timeout=None):
        """Specialized fetching using XML RPCs."""
        packages = xmlrpc.client.ServerProxy(uri).list_packages()
        content = list(packages)

        temp_file = get_temp_file("PypiIndexVisitor")
        with codecs.open(temp_file, mode="wb", encoding="utf-8") as expect:
            json.dump(content, expect, indent=2, separators=(",", ":"))
        return temp_file

    def dumps(self, content):
        """Return None as the content is huge json and should not be dumped."""
        return None

    def get_uris(self, content):
        with codecs.open(content, mode="rb", encoding="utf-8") as contentfile:
            packages_list = json.load(contentfile)

            url_template = "https://pypi.python.org/pypi/{name}/json"
            for name in packages_list:
                package_url = PackageURL(type="pypi", name=name).to_string()
                yield URI(
                    uri=url_template.format(name=name),
                    package_url=package_url,
                    source_uri=self.uri,
                )


@visit_router.route("https://pypi.python.org/pypi/[^/]+/json")
class PypiPackageVisitor(HttpJsonVisitor):
    """
    Collect package metadata URIs for all release of a single Pypi package.
    The url will contain only the package name, for example: https://pypi.org/pypi/vmock/json
    By parsing the content, the goal is to form the json with version/release: https://pypi.org/pypi/vmock/0.1/json
    """

    def get_uris(self, content):
        url_template = "https://pypi.python.org/pypi/{name}/{release}/json"
        info = content.get("info", {})
        name = info.get("name")
        if name:
            for release in content["releases"]:
                package_url = PackageURL(type="pypi", name=name, version=release).to_string()
                yield URI(
                    uri=url_template.format(name=name, release=release),
                    package_url=package_url,
                    source_uri=self.uri,
                )


@visit_router.route("https://pypi.python.org/pypi/[^/]+/[^/]+/json")
class PypiPackageReleaseVisitor(HttpJsonVisitor):
    """
    Collect package download URIs for all packages archives of one Pypi package
    release. The example is: https://pypi.org/pypi/vmock/0.1/json
    """

    def get_uris(self, content):
        # TODO: this is likely best ignored entirely???
        # A download_url may be provided for an off-Pypi-download
        info = content.get("info", {})
        name = info.get("name")
        version = None
        download_url = info.get("download_url")
        if download_url and download_url != "UNKNOWN":
            version = info.get("version")
            package_url = PackageURL(type="pypi", name=name, version=version).to_string()
            yield URI(uri=download_url, package_url=package_url, source_uri=self.uri)

        # Common on-Pypi-download URLs are in the urls block
        for download in content.get("urls", {}):
            url = download.get("url")
            if not url:
                continue
            package_url = PackageURL(type="pypi", name=name, version=version).to_string()
            digests = download.get("digests")
            if digests:
                sha256_digest = digests.get("sha256")
            else:
                sha256_digest = None
            yield URI(
                url,
                package_url=package_url,
                file_name=download.get("filename"),
                size=download.get("size"),
                date=download.get("upload_time"),
                md5=download.get("md5_digest"),
                sha256=sha256_digest,
                source_uri=self.uri,
            )


@map_router.route("https://pypi.python.org/pypi/[^/]+/[^/]+/json")
class PypiPackageMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield ScannedPackages built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        # FIXME: JSON deserialization should be handled eventually by the framework
        metadata = json.loads(resource_uri.data)
        return build_packages(metadata, resource_uri.package_url)


def build_packages(metadata, purl=None):
    """
    Yield ScannedPackage built from Pypi a `metadata` mapping
    for a single package version.
    Yield as many Package as there are download URLs.

    The metadata for a Pypi package has three main blocks: info, releases and
    urls. Releases is redundant with urls and contains all download urls for
    every releases. It is repeased for each version-specific json: we ignore it
    and use only info and urls.

    purl: String value of the package url of the ResourceURI object
    """
    info = metadata["info"]
    # mapping of information that are common to all the downloads of a version
    short_desc = info.get("summary")
    long_desc = info.get("description")
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = "\n".join(descriptions)
    common_data = dict(
        name=info["name"],
        version=info["version"],
        description=description,
        homepage_url=info.get("home_page"),
        bug_tracking_url=info.get("bugtrack_url"),
    )

    author = info.get("author")
    email = info.get("author_email")
    if author or email:
        parties = common_data.get("parties")
        if not parties:
            common_data["parties"] = []
        common_data["parties"].append(
            scan_models.Party(
                type=scan_models.party_person, name=author, role="author", email=email
            )
        )

    maintainer = info.get("maintainer")
    email = info.get("maintainer_email")
    if maintainer or email:
        parties = common_data.get("parties")
        if not parties:
            common_data["parties"] = []
        common_data["parties"].append(
            scan_models.Party(
                type=scan_models.party_person,
                name=maintainer,
                role="maintainer",
                email=email,
            )
        )

    extracted_license_statement = []
    lic = info.get("license")
    if lic and lic != "UNKNOWN":
        extracted_license_statement.append(lic)

    classifiers = info.get("classifiers")
    if classifiers and not extracted_license_statement:
        licenses = [lic for lic in classifiers if lic.lower().startswith("license")]
        for lic in licenses:
            extracted_license_statement.append(lic)

    common_data["extracted_license_statement"] = extracted_license_statement

    kw = info.get("keywords")
    if kw:
        common_data["keywords"] = [k.strip() for k in kw.split(",") if k.strip()]

    # FIXME: we should either support "extra" data in a ScannedPackage or just ignore this kind of FIXME comments for now

    # FIXME: not supported in ScanCode Package: info.platform may provide some platform info (possibly UNKNOWN)
    # FIXME: not supported in ScanCode Package: info.docs_url
    # FIXME: not supported in ScanCode Package: info.release_url "http://pypi.python.org/pypi/Django/1.10b1"
    # FIXME: not supported in ScanCode Package: info.classifiers: this contains a lot of other info (platform, license, etc)
    # FIXME: if the homepage is on Github we can infer the VCS
    # FIXME: info.requires_dist contains a list of requirements/deps that should be mapped to dependencies?
    # FIXME: info.requires_python may be useful and should be mapped to some platform?
    # FIXME: Package Index Owner: seems to be only available on the web page

    # A download_url may be provided for off Pypi download: we yield a package if relevant
    # FIXME: do not prioritize the download_url outside Pypi over actual exact Pypi download URL
    download_url = info.get("download_url")
    if download_url and download_url != "UNKNOWN":
        download_data = dict(
            datasource_id="pypi_sdist_pkginfo",
            type="pypi",
            download_url=download_url,
        )
        download_data.update(common_data)
        package = scan_models.PackageData.from_data(download_data)
        # TODO: Consider creating a DatafileHandler for PyPI API metadata
        package.datasource_id = "pypi_api_metadata"
        package.set_purl(purl)
        yield package

    # yield a package for each download URL
    for download in metadata["urls"]:
        url = download.get("url")
        if not url:
            continue

        packagetype = None
        if download.get("packagetype") == "sdist":
            packagetype = "pypi_sdist_pkginfo"
        else:
            packagetype = "pypi_bdist_pkginfo"

        download_data = dict(
            download_url=url,
            size=download.get("size"),
            release_date=parse_date(download.get("upload_time")),
            datasource_id=packagetype,
            type="pypi",
        )
        # TODO: Check for other checksums
        download_data["md5"] = download.get("md5_digest")
        digests = download.get("digests")
        if digests and (sha256_digest := digests.get("sha256")):
            download_data["sha256"] = sha256_digest
        download_data.update(common_data)
        package = scan_models.PackageData.from_data(download_data)
        package.datasource_id = "pypi_api_metadata"

        if purl:
            purl_str = purl.to_string()
            purl_filename_qualifiers = purl_str + "?file_name=" + download.get("filename")
            updated_purl = PackageURL.from_string(purl_filename_qualifiers)
            package.set_purl(updated_purl)
        else:
            package.set_purl(purl)

        yield package
