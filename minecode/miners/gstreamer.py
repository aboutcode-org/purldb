#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from bs4 import BeautifulSoup
from commoncode import fileutils
from commoncode.fileutils import file_base_name
from packagedcode import models as scan_models
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpVisitor
from minecode.miners import Mapper


class GstreamerSeed(seed.Seeder):
    is_active = False

    def get_seeds(self):
        yield "https://gstreamer.freedesktop.org/src/"


@visit_router.route(r"https://gstreamer.freedesktop.org/src/([\w\-\.]+/)*")
class GstreamerHTMLVisitor(HttpVisitor):
    """
    Visit the HTML page of gstreamer. Yield the uri which can be used for the next visitor use or the uri stands for the file resource.
    The regex is to match:
    https://gstreamer.freedesktop.org/src/
    https://gstreamer.freedesktop.org/src/gst-openmax/pre/
    """

    def get_uris(self, content):
        page = BeautifulSoup(content, "lxml")
        url_template = self.uri + "{sub_path}"
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue
            href = a["href"]
            if href:
                # For parent folder link or other unrelated links, ignore
                if href.startswith("/") or href.startswith("?"):
                    continue
                if href.endswith("/"):
                    # If the path is folder, yield it for the next visitor use.
                    yield URI(
                        uri=url_template.format(sub_path=href), source_uri=self.uri
                    )
                else:
                    # If it's the file resource, form the package_url and yield the URI with package url info
                    # For example: gst-openmax-0.10.0.4.tar.bz2
                    file_name = href
                    file_name_without_prefix = file_base_name(file_name)
                    if "-" in file_name_without_prefix:
                        project_name_versions = file_name.rpartition("-")
                        project_name = project_name_versions[0]
                        version = project_name_versions[-1]
                    else:
                        project_name = file_name
                        version = None
                    package_url = PackageURL(
                        type="gstreamer", name=project_name, version=version
                    ).to_string()
                    yield URI(
                        uri=url_template.format(sub_path=href),
                        package_url=package_url,
                        file_name=file_name,
                        source_uri=self.uri,
                    )


@map_router.route(
    "https://gstreamer.freedesktop.org/src/([\\w\\-\\.]+/)*[\\w\\-\\.]+[.tar\\.bz2\\.gz|\\.tar\\.xz]"
)
class GstreamerURLMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        """
        return build_package_from_url(resource_uri.uri, resource_uri.package_url)


def build_package_from_url(uri, purl=None):
    """
    Return Package built from uri and package_url.
    uri: String value of uri of the ResourceURI object.
    purl: String value of the package url of the ResourceURI object
    """
    file_name = fileutils.file_name(uri)
    file_name_without_prefix = file_name
    prefixes = (".tar.bz2", ".tar.gz", ".tar.xz")
    for prefix in prefixes:
        file_name_without_prefix = file_name_without_prefix.replace(prefix, "")
    if "-" in file_name_without_prefix:
        project_name, _, version = file_name.rpartition("-")
        common_data = dict(
            type="gstreamer",
            name=project_name,
            version=version,
            download_url=uri,
            homepage_url="https://gstreamer.freedesktop.org",
        )
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
