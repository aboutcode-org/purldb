import logging

import attr
import requests
from debian_inspector.version import Version as DebVersion
from packagedcode import models as scan_models
from packagedcode.debian import DebianDscFileHandler
from packagedcode.debian_copyright import StandaloneDebianCopyrightFileHandler
from packageurl import PackageURL

from minecode import priority_router
from minecode.utils import fetch_and_write_file_from_url
from minecode.utils import get_package_sha1
from packagedb.models import PackageContentType
from packagedb.models import PackageRelation
from packagedb.models import make_relationship

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


DEBIAN_BASE_URL = "https://deb.debian.org/debian/pool/main/"
DEBIAN_METADATA_URL = "https://metadata.ftp-master.debian.org/changelogs/main/"

UBUNTU_BASE_URL = "http://archive.ubuntu.com/ubuntu/pool/main/"
UBUNTU_METADATA_URL = "http://changelogs.ubuntu.com/changelogs/pool/main/"


@priority_router.route("pkg:deb/.*")
def process_request(purl_str, **kwargs):
    """
    Process `priority_resource_uri` containing a maven Package URL (PURL) as a
    URI.

    This involves obtaining Package information for the PURL from debian and
    using it to create a new PackageDB entry. The binary package is then added to the
    scan queue afterwards. We also get the Package information for the
    accompanying source package and add it to the PackageDB and scan queue, if
    available.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    from minecode.model_utils import DEFAULT_PIPELINES

    source_purl = kwargs.get("source_purl", None)
    addon_pipelines = kwargs.get("addon_pipelines", [])
    pipelines = DEFAULT_PIPELINES + tuple(addon_pipelines)
    priority = kwargs.get("priority", 0)

    try:
        package_url = PackageURL.from_string(purl_str)
        source_package_url = None
        if source_purl:
            source_package_url = PackageURL.from_string(source_purl)

    except ValueError as e:
        error = f"error occured when parsing purl: {purl_str} source_purl: {source_purl} : {e}"
        return error

    has_version = bool(package_url.version)
    if has_version:
        error = map_debian_metadata_binary_and_source(
            package_url=package_url,
            source_package_url=source_package_url,
            pipelines=pipelines,
            priority=priority,
        )

    return error


def map_debian_package(debian_package, package_content, pipelines, priority=0):
    """
    Add a debian `package_url` to the PackageDB.

    Return an error string if errors have occured in the process.
    """
    from minecode.model_utils import add_package_to_scan_queue
    from minecode.model_utils import merge_or_create_package

    db_package = None
    error = ""

    purl = debian_package.package_url
    if package_content == PackageContentType.BINARY:
        download_url = debian_package.binary_archive_url
    elif package_content == PackageContentType.SOURCE_ARCHIVE:
        download_url = debian_package.source_archive_url

    response = requests.get(download_url)
    if not response.ok:
        msg = f"Package metadata does not exist on debian: {download_url}"
        error += msg + "\n"
        logger.error(msg)
        return db_package, error

    purl_package = scan_models.PackageData(
        type=purl.type,
        namespace=purl.namespace,
        name=purl.name,
        version=purl.version,
        qualifiers=purl.qualifiers,
    )

    package, error_metadata = get_debian_package_metadata(debian_package)
    if not package:
        error += error_metadata
        return db_package, error

    package_copyright, error_copyright = get_debian_package_copyright(debian_package)
    package.update_purl_fields(package_data=purl_package, replace=True)
    if package_copyright:
        update_license_copyright_fields(
            package_from=package_copyright,
            package_to=package,
            replace=True,
        )
    else:
        error += error_metadata

    # This will be used to download and scan the package
    package.download_url = download_url

    # Set package_content value
    package.extra_data["package_content"] = package_content

    # If sha1 exists for an archive, we know we can create the package
    # Use purl info as base and create packages for binary and source package
    sha1 = get_package_sha1(package=package, field="download_url")
    if sha1:
        package.sha1 = sha1
        db_package, _, _, _ = merge_or_create_package(package, visit_level=50)
    else:
        msg = f"Failed to retrieve package archive: {purl.to_string()} from url: {download_url}"
        error += msg + "\n"
        logger.error(msg)

    # Submit package for scanning
    if db_package:
        add_package_to_scan_queue(db_package, pipelines, priority)

    return db_package, error


def get_debian_package_metadata(debian_package):
    """
    Given a DebianPackage object with package url and source package url
    information, get the .dsc package metadata url, fetch the .dsc file,
    parse and return the PackageData object containing the package metadata
    for that Debian package.

    If there are errors, return None and a string containing the error
    information.
    """
    error = ""

    metadata_url = debian_package.package_metadata_url
    temp_metadata_file = fetch_and_write_file_from_url(url=metadata_url)
    if not temp_metadata_file:
        msg = f"Package metadata does not exist on debian: {metadata_url}"
        error += msg + "\n"
        logger.error(msg)
        return None, error

    packages = DebianDscFileHandler.parse(location=temp_metadata_file)
    package = list(packages).pop()

    package.qualifiers = debian_package.package_url.qualifiers

    return package, error


def get_debian_package_copyright(debian_package):
    """
    Given a DebianPackage object with package url and source package url
    information, get the debian copyright file url, fetch and run license
    detection, and return the PackageData object containing the package
    metadata for that Debian package.

    If there are errors, return None and a string containing the error
    information.
    """
    error = ""

    metadata_url = debian_package.package_copyright_url
    temp_metadata_file = fetch_and_write_file_from_url(url=metadata_url)
    if not temp_metadata_file:
        msg = f"Package metadata does not exist on debian: {metadata_url}"
        error += msg + "\n"
        logger.error(msg)
        return None, error

    packages = StandaloneDebianCopyrightFileHandler.parse(location=temp_metadata_file)
    package = list(packages).pop()

    package.qualifiers = debian_package.package_url.qualifiers

    return package, error


def update_license_copyright_fields(package_from, package_to, replace=True):
    fields_to_update = [
        "copyright",
        "holder",
        "declared_license_expression",
        "declared_license_expression_spdx",
        "license_detections",
        "other_license_expression",
        "other_license_expression_spdx",
        "other_license_detections",
        "extracted_license_statement",
    ]

    for field in fields_to_update:
        value = getattr(package_from, field)
        if value and replace:
            setattr(package_to, field, value)


def map_debian_metadata_binary_and_source(
    package_url, source_package_url, pipelines, priority=0
):
    """
    Get metadata for the binary and source release of the Debian package
    `package_url` and save it to the PackageDB.

    Return an error string for errors that occur, or empty string if there is no error.
    """
    error = ""

    if "repository_url" in package_url.qualifiers:
        base_url = package_url.qualifiers["repository_url"]
    elif package_url.namespace == "ubuntu":
        base_url = UBUNTU_BASE_URL
    else:
        base_url = DEBIAN_BASE_URL

    if "api_data_url" in package_url.qualifiers:
        metadata_base_url = package_url.qualifiers["api_data_url"]
    elif package_url.namespace == "ubuntu":
        metadata_base_url = UBUNTU_METADATA_URL
    else:
        metadata_base_url = DEBIAN_METADATA_URL

    package_urls = dict(
        package_url=package_url,
        source_package_url=source_package_url,
        archive_base_url=base_url,
        metadata_base_url=metadata_base_url,
    )
    debian_package, emsg = DebianPackage.from_purls(package_urls)
    if emsg:
        return emsg

    binary_package, emsg = map_debian_package(
        debian_package,
        PackageContentType.BINARY,
        pipelines,
        priority,
    )
    if emsg:
        error += emsg

    package_url.qualifiers["classifier"] = "sources"
    source_package, emsg = map_debian_package(
        debian_package,
        PackageContentType.SOURCE_ARCHIVE,
        pipelines,
        priority,
    )
    if emsg:
        error += emsg

    if binary_package and source_package:
        make_relationship(
            from_package=binary_package,
            to_package=source_package,
            relationship=PackageRelation.Relationship.SOURCE_PACKAGE,
        )

    return error


@attr.s
class DebianPackage:
    """
    Contains the package url and source package url for a debian package
    necessary to get source, binary, metadata and copyright urls for it.
    """

    archive_base_url = attr.ib(type=str)
    metadata_base_url = attr.ib(type=str)
    package_url = attr.ib(type=str)
    source_package_url = attr.ib(type=str)
    metadata_directory_url = attr.ib(type=str, default=None)
    archive_directory_url = attr.ib(type=str, default=None)

    @classmethod
    def from_purls(cls, package_urls):
        """Set the directory URLs for metadata and package archives."""
        debian_package = cls(**package_urls)
        error = debian_package.set_debian_directories()
        return debian_package, error

    @property
    def package_archive_version(self):
        """
        Get the useful part of the debian package version used in
        source, binary, metadata and copyright URLs optionally.
        """
        debvers = DebVersion.from_string(self.package_url.version)
        if debvers.revision != "0":
            purl_version = f"{debvers.upstream}-{debvers.revision}"
        else:
            purl_version = debvers.upstream
        return purl_version

    @property
    def binary_archive_url(self):
        """Get the .deb debian binary archive url for this debian package."""
        purl_version = self.package_archive_version
        arch = self.package_url.qualifiers.get("arch")
        if arch:
            archive_name = f"{self.package_url.name}_{purl_version}_{arch}.deb"
        else:
            archive_name = f"{self.package_url.name}_{purl_version}.deb"
        binary_package_url = self.archive_directory_url + f"{archive_name}"
        return binary_package_url

    @property
    def source_archive_url(self):
        """Get the debian source tarball archive url for this debian package."""
        debian_source_archive_formats = [
            ".tar.xz",
            ".tar.gz",
            ".orig.tar.xz",
            ".orig.tar.gz",
            ".orig.tar.bz2",
        ]

        source_version = self.package_archive_version
        if not self.source_package_url:
            source_package_name = self.package_url.name
        else:
            source_package_name = self.source_package_url.name
            if self.source_package_url.version:
                source_version = self.source_package_url.version

        for archive_format in debian_source_archive_formats:
            if ".orig" in archive_format:
                base_version_source = source_version.split("-")[0]
                archive_name = (
                    f"{source_package_name}_{base_version_source}" + archive_format
                )
            else:
                archive_name = (
                    f"{source_package_name}_{source_version}" + archive_format
                )
            source_package_url = self.archive_directory_url + archive_name
            response = requests.get(source_package_url)
            if response.ok:
                break

        return source_package_url

    @property
    def package_metadata_url(self):
        """Get the .dsc metadata file url for this debian package."""
        metadata_version = self.package_archive_version
        if not self.source_package_url:
            metadata_package_name = self.package_url.name
        else:
            metadata_package_name = self.source_package_url.name
            if self.source_package_url.version:
                metadata_version = self.source_package_url.version

        base_version_metadata = metadata_version.split("+")[0]
        metadata_dsc_package_url = (
            self.archive_directory_url
            + f"{metadata_package_name}_{base_version_metadata}.dsc"
        )
        response = requests.get(metadata_dsc_package_url)
        if not response.ok:
            metadata_dsc_package_url = (
                self.archive_directory_url
                + f"{metadata_package_name}_{metadata_version}.dsc"
            )

        return metadata_dsc_package_url

    @property
    def package_copyright_url(self):
        """
        Get the debian copyright file url containing license and copyright
        declarations for this debian package.
        """
        # Copyright files for ubuntu are named just `copyright` and placed under a name-version folder
        # instead of having the name-version in the copyright file itself
        copyright_file_string = "_copyright"
        if self.package_url.namespace == "ubuntu":
            copyright_file_string = "/copyright"

        metadata_version = self.package_archive_version
        if not self.source_package_url:
            metadata_package_name = self.package_url.name
        else:
            metadata_package_name = self.source_package_url.name
            if self.source_package_url.version:
                metadata_version = self.source_package_url.version

        copyright_package_url = (
            self.metadata_directory_url
            + f"{metadata_package_name}_{metadata_version}{copyright_file_string}"
        )
        response = requests.get(copyright_package_url)
        if not response.ok:
            base_version_metadata = metadata_version.split("+")[0]
            copyright_package_url = (
                self.metadata_directory_url
                + f"{metadata_package_name}_{base_version_metadata}{copyright_file_string}"
            )

        return copyright_package_url

    def set_debian_directories(self):
        """
        Compute and set base urls for metadata and archives, to get
        source/binary
        """
        error = ""

        archive_base_url = self.archive_base_url
        metadata_base_url = self.metadata_base_url

        index_folder = None
        if self.package_url.name.startswith("lib"):
            name_wout_lib = self.package_url.name.replace("lib", "")
            index_folder = "lib" + name_wout_lib[0]
        else:
            index_folder = self.package_url.name[0]

        msg = "No directory exists for package at: "

        package_directory = f"{archive_base_url}{index_folder}/{self.package_url.name}/"
        metadata_directory = (
            f"{metadata_base_url}{index_folder}/{self.package_url.name}/"
        )

        response = requests.get(package_directory)
        if not response.ok:
            if not self.source_package_url:
                error = msg + str(package_directory)
                return error

            if self.source_package_url.name.startswith("lib"):
                name_wout_lib = self.source_package_url.name.replace("lib", "")
                index_folder = "lib" + name_wout_lib[0]
            else:
                index_folder = self.source_package_url.name[0]

            package_directory = (
                f"{archive_base_url}{index_folder}/{self.source_package_url.name}/"
            )
            metadata_directory = (
                f"{metadata_base_url}{index_folder}/{self.source_package_url.name}/"
            )

            response = requests.get(package_directory)
            if not response.ok:
                error = msg + str(package_directory)
                return error

        self.archive_directory_url = package_directory
        self.metadata_directory_url = metadata_directory


# FIXME: We are not returning download URLs. Returned information is incorrect


def get_dependencies(data):
    """Return a list of DependentPackage extracted from a Debian `data` mapping."""
    scopes = {
        "Build-Depends": dict(is_runtime=False, is_optional=True),
        "Depends": dict(is_runtime=True, is_optional=False),
        "Pre-Depends": dict(is_runtime=True, is_optional=False),
        # 'Provides': dict(is_runtime=True, is_optional=False),
        # 'Recommends': dict(is_runtime=True, is_optional=True),
        # 'Suggests': dict(is_runtime=True, is_optional=True),
    }
    dep_pkgs = []
    for scope, flags in scopes.items():
        depends = data.get(scope)
        if not depends:
            continue

        dependencies = None  # debutils.comma_separated(depends)
        if not dependencies:
            continue
        # break each dep in package names and version constraints
        # FIXME:!!!
        for name in dependencies:
            purl = PackageURL(type="deb", namespace="debian", name=name)
            dep = scan_models.DependentPackage(
                purl=purl.to_string(), score=scope, **flags
            )
            dep_pkgs.append(dep)

    return dep_pkgs


def get_vcs_repo(description):
    """Return a tuple of (vcs_tool, vcs_repo) or (None, None) if no vcs_repo is found."""
    repos = []
    for vcs_tool, vcs_repo in description.items():
        vcs_tool = vcs_tool.lower()
        if not vcs_tool.startswith("vcs-") or vcs_tool.startswith("vcs-browser"):
            continue
        _, _, vcs_tool = vcs_tool.partition("-")
        repos.append((vcs_tool, vcs_repo))

    if len(repos) > 1:
        raise TypeError(f"Debian description with more than one Vcs repos: {repos}")

    if repos:
        vcs_tool, vcs_repo = repos[0]
    else:
        vcs_tool = None
        vcs_repo = None

    return vcs_tool, vcs_repo
