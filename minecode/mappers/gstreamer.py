#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from commoncode import fileutils
from packagedcode import models as scan_models

from minecode import map_router
from minecode.mappers import Mapper


@map_router.route('https://gstreamer.freedesktop.org/src/([\w\-\.]+/)*[\w\-\.]+[.tar\.bz2\\.gz|\.tar\.xz]')
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
    prefixes = ('.tar.bz2', '.tar.gz', '.tar.xz')
    for prefix in prefixes:
        file_name_without_prefix = file_name_without_prefix.replace(prefix, '')
    if '-' in file_name_without_prefix:
        project_name, _, version = file_name.rpartition('-')
        common_data = dict(
            type='gstreamer',
            name=project_name,
            version=version,
            download_url=uri,
            homepage_url='https://gstreamer.freedesktop.org'
        )
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package
