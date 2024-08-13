#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from packagedcode import models as scan_models
from packagedcode.models import DependentPackage
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import Mapper


class BowerSeed(seed.Seeder):
    def get_seeds(self):
        yield "https://registry.bower.io/packages"


@visit_router.route("https://registry.bower.io/packages")
class BowerTopJsonVisitor(HttpJsonVisitor):
    """Collect URIs for all packages from the json returned."""

    def get_uris(self, content):
        """
        The json content is a list with name and url, like the following format:
        ...
          {
            "name": "bello",
            "url": "https://github.com/QiaoBuTang/bello.git"
          },
          {
            "name": "bello-gfw",
            "url": "https://gitcafe.com/GilbertSun/bello.git"
          },
        ...
        The url could be in the following formats like github, loglg, gitcafe, bitbuckets etc.
        # FIXME: We should cover all urls beyond the above four categories.
        """
        github_base_url = (
            "https://raw.githubusercontent.com/{owner}/{name}/master/bower.json"
        )
        lolg_base_url = "https://lolg.it/{owner}/{name}/raw/master/bower.json"
        gitcafe_base_url = (
            "https://coding.net/u/{owner}/p/{name}/git/raw/master/bower.json"
        )
        bitbucket_base_url = (
            "https://bitbucket.org/{owner}/{name}/raw/master/bower.json"
        )
        base_url_map = {
            "https://github.com/": github_base_url,
            "https://lolg.it/": lolg_base_url,
            "https://gitcafe.com/": gitcafe_base_url,
            "https://bitbucket.org/": bitbucket_base_url,
        }
        for entry in content:
            name = entry.get("name")
            url = entry.get("url")
            if name in url:
                owner = None
                package_url = PackageURL(type="bower", name=name).to_string()
                for host_name, base_url in base_url_map.iteritems():
                    if url.startswith(host_name):
                        owner = url[len(host_name) : url.index(name) - 1]
                        yield URI(
                            uri=base_url.format(owner=owner, name=name),
                            package_url=package_url,
                            source_uri=self.uri,
                        )


@visit_router.route(
    "https://raw.githubusercontent.com/.*/master/bower.json",
    "https://lolg.it/.*/master/bower.json",
    "https://coding.net/.*/master/bower.json",
    "https://bitbucket.org/*/master/bower.json",
)
class BowerJsonVisitor(HttpJsonVisitor):
    """Collect content of the json itself by the visitor."""

    pass


@map_router.route(
    "https://raw.githubusercontent.com/.*/master/bower.json",
    "https://lolg.it/.*/master/bower.json",
    "https://coding.net/.*/master/bower.json",
)
class BowerJsonMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_jsonfile(
            metadata, resource_uri.uri, resource_uri.package_url
        )


def build_packages_from_jsonfile(metadata, uri=None, purl=None):
    """Yield Package built from Bower json content"""
    content = json.loads(metadata)

    licenses_content = content.get("licenses")
    extracted_license_statement = set([])
    if licenses_content:
        if isinstance(licenses_content, list):
            for lic in licenses_content:
                extracted_license_statement.add(lic)
        else:
            extracted_license_statement.add(licenses_content)

    keywords_content = content.get("keywords", [])
    name = content.get("name")

    devdependencies = content.get("devDependencies")
    dev_dependencies = []
    if devdependencies:
        for key, value in devdependencies.items():
            dev_dependencies.append(
                DependentPackage(
                    purl=key, extracted_requirement=value, scope="devdependency"
                ).to_dict()
            )

    dependencies = content.get("dependencies")
    dependencies_build = []
    if dependencies:
        for key, value in dependencies.items():
            dependencies_build.append(
                DependentPackage(
                    purl=key, extracted_requirement=value, scope="runtime"
                ).to_dict()
            )

    if name:
        vcs_tool, vcs_repo = get_vcs_repo(content)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + "+" + vcs_repo
        common_data = dict(
            type="bower",
            name=name,
            description=content.get("description"),
            version=content.get("version"),
            vcs_url=vcs_repo,
            keywords=keywords_content,
            homepage_url=content.get("homepage"),
            datasource_id="bower_json",
            license_detections=[],
        )

        if extracted_license_statement:
            common_data["extracted_license_statement"] = list(
                extracted_license_statement
            )

        author_content = content.get("author")
        if author_content:
            parties = common_data.get("parties")
            if not parties:
                common_data["parties"] = []
            common_data["parties"].append(
                scan_models.Party(
                    name=author_content,
                    role="author",
                ).to_dict()
            )
        else:
            parties = common_data.get("parties")
            if not parties:
                common_data["parties"] = []
            author_content = content.get("authors", [])
            for author in author_content:
                author_split = author.split(":")
                if len(author_split) > 1:
                    common_data["parties"].append(
                        scan_models.Party(
                            name=author_split[1].strip(),
                            role="author",
                        ).to_dict()
                    )

        dependencies = []
        if dependencies_build:
            dependencies.extend(dependencies_build)
        if dev_dependencies:
            dependencies.extend(dev_dependencies)
        if len(dependencies) > 0:
            common_data["dependencies"] = dependencies
        package = scan_models.Package.from_package_data(
            package_data=common_data,
            datafile_path=uri,
        )
        package.set_purl(purl)
        yield package


def get_vcs_repo(content):
    """Return the repo type and url."""
    repo = content.get("repository", {})
    if repo:
        return repo.get("type"), repo.get("url")
    return None, None
