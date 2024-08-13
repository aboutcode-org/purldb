#
#  Copyright (c) 2016 nexB Inc. and others. All rights reserved.
#


import json
import logging
import os

from commoncode import fileutils
from packagedcode.models import PackageData
from packagedcode.rpm import EVR

from minecode import visit_router
from minecode.utils import extract_file
from minecode.utils import fetch_http
from minecode.utils import get_temp_file
from minecode.visitors import URI
from minecode.visitors import repodata

logger = logging.getLogger(__name__)


"""
Analyzes the "repomd.xml" of a given repository from the URL given as input
and generates a list of RPM objects
"""


def download(uri):
    """
    Fetch the file at uri, saving it to a temp file and return the path to
    this temp file.
    """
    name = fileutils.file_name(uri)
    file_ext = fileutils.file_extension(name)
    name = name.replace(file_ext, "")

    content = fetch_http(uri)
    temp_file = get_temp_file(
        file_name="minecode-fetched-file-" + name, extension=file_ext
    )
    with open(temp_file, "wb") as tmp:
        tmp.write(content)
    file_name = tmp.name
    return file_name


def generate_rpm_objects(package_infos, base_url):
    """Yield Packages from an iterable of RPM infos given a base_url."""
    # FIXME: what does package_infos mean? wheer does it come from?
    for infos in package_infos:
        package_data = dict(
            # FIXME: need to add id back? this is id is some hash which is local to the repo.
            # id=infos.get('pkgid'),
            type="rpm",
            name=infos.get("name"),
            version=EVR(
                epoch=infos.get("epoch"),
                version=infos.get("ver"),
                release=infos.get("rel"),
            ).to_string(),
            description=infos.get("description"),
            homepage_url=infos.get("url"),
            download_url=repodata.build_rpm_download_url(base_url, infos.get("href")),
            extracted_license_statement=infos.get("license", ""),
        )
        package = PackageData.from_data(package_data)
        if infos.get("source_rpm"):
            src_rpm = PackageData(name=infos.get("source_rpm"))
            package.related_packages = [src_rpm]
        yield package


# TODO: refactor, this does not make sense, each are different URIs?
# FIXME: the doc and semantics are cryptic too


def fetch_repomd_subfile(base_url, repomd_xml, subfile):
    """
    Download and extract a subfile('filelists.xml.gz', 'primary.xml.gz',
    'other.xml.gz') of any repodata and return the subfile location.
    """
    url = base_url + repodata.get_url_for_tag(repomd_xml, subfile)
    target_location = extract_file(download(url))
    return os.path.join(target_location, os.listdir(target_location)[0])


@visit_router.route(".+/repomd.xml")
def collect_rpm_packages_from_repomd(uri):
    """Collect RPM data from yum repository repomd.xml."""
    base_url = fileutils.parent_directory(fileutils.parent_directory(uri))
    repomd_xml = download(uri)

    filelists_xml = fetch_repomd_subfile(base_url, repomd_xml, "filelists")
    primary_xml = fetch_repomd_subfile(base_url, repomd_xml, "primary")
    other_xml = fetch_repomd_subfile(base_url, repomd_xml, "other")

    pkg_infos = repodata.get_pkg_infos(filelists_xml, primary_xml, other_xml)

    rpms = list(generate_rpm_objects(pkg_infos, base_url))
    uris = []
    for rpm in rpms:
        if rpm.download_url:
            uris.append(URI(uri=rpm.download_url))
    return uris, json.dumps([r.to_dict() for r in rpms]), None
