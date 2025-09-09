#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from packagedcode import models as scan_models
from packageurl import PackageURL
from packageurl.contrib.purl2url import build_golang_download_url

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import Mapper
from minecode.miners import NonPersistentHttpVisitor
from minecode.utils import form_vcs_url


class GoLangSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://api.godoc.org/packages"


@visit_router.route("https://api.godoc.org/packages")
class GodocIndexVisitor(NonPersistentHttpVisitor):
    """Collect Golang URIs for packages available in the Go doc index."""

    def get_uris(self, content):
        """Return URIs to search the API further for a package"""
        seen_paths = set()
        for path, package in get_packages(content):
            package_url, path = parse_package_path(path)
            if path in seen_paths:
                continue
            seen_paths.add(path)

            # note the addition of a * at the end of the search string...
            # without this the returned data are sparse
            details_url = "https://api.godoc.org/search?q={path}*".format(**locals())
            host = get_well_known_host(path)
            # If the path belongs github/bitbucket, yield a repo too
            if host:
                # keep github, bitbucket... as type:
                repo_type, _, _ = host.lower().partition(".")  # NOQA
                repo_url = "https://{namespace}/{name}".format(**package_url.to_dict())
                repo_purl = PackageURL(
                    type=repo_type,
                    namespace=package_url.namespace,
                    name=package_url.name,
                    qualifiers=dict(package_url=package_url.to_string()),
                ).to_string()

                yield URI(uri=repo_url, package_url=repo_purl, source_uri=self.uri)

                yield URI(
                    uri=details_url,
                    package_url=package_url.to_string(),
                    source_uri=self.uri,
                )

            else:
                yield URI(uri=details_url, package_url=package_url, source_uri=self.uri)


@visit_router.route(r"https://api\.godoc\.org/search\?q=.*")
class GodocSearchVisitor(NonPersistentHttpVisitor):
    """Collect URIs and data through the godoc searchi API."""

    def get_uris(self, content):
        seen_paths = set()
        for path, package in get_packages(content):
            package_url, path = parse_package_path(path)
            if path in seen_paths:
                continue
            seen_paths.add(path)

            purl = package_url.to_string()
            yield URI(
                # NOTE: here we use a previsited PURL as URI
                uri=purl,
                package_url=purl,
                source_uri=self.uri,
                # the data contains some popcounts and a description
                data=package,
                visited=True,
            )


def get_packages(packages_json_location):
    """
    Yield a path and mapping of Go package raw data from a JSON data location.
    {
      "name": "aws",
      "path": "github.com/aws/aws-sdk-go/aws",
      "import_count": 13623,
      "synopsis": "Package aws provides the core SDK's utilities and shared types.",
      "stars": 4218,
      "score": 0.99
    },
    """
    with open(packages_json_location) as f:
        data = json.load(f)
    for package in data.get("results", []):
        path = package["path"]
        if path and not is_standard_import(path):
            yield path, package


def is_standard_import(path):
    """Return True if a Go import path is for a standard library import"""
    standard_packages = (
        "archive",
        "bufio",
        "builtin",
        "bytes",
        "compress",
        "container",
        "context",
        "crypto",
        "database",
        "debug",
        "encoding",
        "expvar",
        "flag",
        "fmt",
        "go",
        "hash",
        "html",
        "image",
        "index",
        "io",
        "log",
        "math",
        "mime",
        "net",
        "os",
        "path",
        "plugin",
        "reflect",
        "regexp",
        "runtime",
        "sort",
        "strconv",
        "strings",
        "sync",
        "syscall",
        "testing",
        "text",
        "time",
        "unsafe",
        "golang.org/x/benchmarks",
        "golang.org/x/blog",
        "golang.org/x/build",
        "golang.org/x/crypto",
        "golang.org/x/debug",
        "golang.org/x/image",
        "golang.org/x/mobile",
        "golang.org/x/net",
        "golang.org/x/perf",
        "golang.org/x/review",
        "golang.org/x/sync",
        "golang.org/x/sys",
        "golang.org/x/text",
        "golang.org/x/time",
        "golang.org/x/tools",
        "golang.org/x/tour",
        "golang.org/x/exp",
    )

    return path.startswith(standard_packages)


repo_hosters = "bitbucket.org/", "github.com/", "gitlab.com/"


def get_well_known_host(path):
    """Return a host if this path is from a well known hoster or None."""
    if path.startswith(repo_hosters):
        host, _, _ = path.partition(".")
        return host


def parse_package_path(path):
    """Return a PackageURL and transformed path given a path to a Go import."""
    path = path or ""
    segments = path.split("/")

    host = get_well_known_host(path)
    qualifiers = None
    if host:
        # keep only the first few segments
        segments = segments[:3]
        repo_url = "https://" + "/".join(segments)
        qualifiers = dict(vcs_repository=repo_url)
    namespace = None
    if len(segments) > 1:
        namespace = segments[:-1]
        namespace = "/".join(namespace)

    name = segments[-1]

    path = "/".join(segments)

    package_url = PackageURL(type="golang", namespace=namespace, name=name, qualifiers=qualifiers)

    return package_url, path


@map_router.route("pkg:golang/.*")
class GolangApiDocMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        package = json.loads(resource_uri.data)
        yield build_golang_package(package, resource_uri.package_url)


def build_golang_package(package_data, purl):
    """Return a single Golang package"""
    package_url = PackageURL.from_string(purl)
    vcs_url = package_url.qualifiers.get("vcs_repository")
    homepage_url = "/".join(["https:/", package_url.namespace, package_url.name])
    vcs_tool = "git" if "github.com" in package_url.namespace else None
    if vcs_tool:
        vcs_url = form_vcs_url(vcs_tool, vcs_url)
    # TODO: collect stats and counter from package_data too
    package = scan_models.Package(
        name=package_url.name,
        namespace=package_url.namespace,
        type=package_url.type,
        primary_language="Go",
        description=package_data.get("synopsis"),
        homepage_url=homepage_url,
        vcs_url=vcs_url,
    )
    return package


def build_golang_generic_package(package_data, package_url):
    """Return a single Golang package"""
    homepage_url = "/".join(["https:/", package_url.namespace, package_url.name])
    license_text = package_data.get("licenses")
    extracted_license_statement = [license_text]

    purl_str = package_url.to_string()
    download_url = build_golang_download_url(purl_str)

    common_data = dict(
        name=package_url.name,
        namespace=package_url.namespace,
        type=package_url.type,
        primary_language="go",
        homepage_url=homepage_url,
        extracted_license_statement=extracted_license_statement,
        download_url=download_url,
    )

    package = scan_models.PackageData.from_data(common_data)
    package.set_purl(package_url)
    yield package
