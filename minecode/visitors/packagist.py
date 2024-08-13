#
# Copyright (c) 2017 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#


from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.visitors import URI
from minecode.visitors import HttpJsonVisitor

"""
Collect packagist packages

The packagist repo API is at: https://packagist.org/apidoc
"""


class PackagistSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://packagist.org/packages/list.json"


@visit_router.route("https://packagist.org/packages/list.json")
class PackagistListVisitor(HttpJsonVisitor):
    """
    Collect list json resource and yield URIs for searching with package url.

    The yield uri format is like: https://packagist.org/p/[vendor]/[package].json
    """

    def get_uris(self, content):
        search_url_template = "https://packagist.org/p/{vendor}/{package}.json"
        packages_entries = content.get("packageNames", {})
        for package in packages_entries:
            # FIXME: what does it mean to have no / in the URL?
            if "/" not in package:
                continue
            vp = package.split("/")
            vendor = vp[0]
            package = vp[1]
            package_url = PackageURL(type="composer", name=package).to_string()
            yield URI(
                uri=search_url_template.format(vendor=vendor, package=package),
                package_url=package_url,
                source_uri=self.uri,
            )


@visit_router.route("https://packagist.org/p/.*json")
class PackageVisitor(HttpJsonVisitor):
    """Collect JSON for a package."""

    # FIXME: what about having a download URL to fetch the real package???
    pass
