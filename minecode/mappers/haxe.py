#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from packagedcode.haxe import HaxelibJsonHandler

from minecode import map_router
from minecode.mappers import Mapper


@map_router.route(
    r"https://lib.haxe.org/p/[\w\-\.]+/[\w\-\.]+/raw-files/[\w\-\.]+/package.json"
)
class HaxePackageJsonMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """Yield Package built from package json file."""
        # FIXME: JSON deserialization should be handled eventually by the framework
        metadata = json.loads(resource_uri.data)
        return build_packages_with_json(metadata, resource_uri.package_url)


def build_packages_with_json(metadata, purl=None):
    # yield package by getting package from the build_package parser in scancode
    package = HaxelibJsonHandler._parse(json_data=metadata)
    if package:
        package.set_purl(purl)
        yield package
