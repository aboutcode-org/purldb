#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

import packagedcode.models as scan_models
import saneyaml
from bs4 import BeautifulSoup
from packageurl import PackageURL

from minecode import map_router
from minecode import seed
from minecode import visit_router
from minecode.miners import URI
from minecode.miners import HttpJsonVisitor
from minecode.miners import HttpVisitor
from minecode.miners import Mapper
from minecode.utils import parse_date


class CpanSeed(seed.Seeder):
    def get_seeds(self):
        yield "http://www.cpan.org/modules/01modules.index.html"
        author_search_template = (
            "https://fastapi.metacpan.org/author/_search?q=email:{char}*&size=5000"
        )
        for char in "abcdefghijklmnopqrstuvwxyz".split():
            yield author_search_template.format(char)


# The idea of CPAN API visitor is based on
# https://github.com/metacpan/metacpan-api/blob/master/docs/API-docs.md
#
# From the doc: You can certainly scroll if you are fetching less than 5,000
# items. You might want to do this if you are expecting a large data set, but
# will still need to run many requests to get all of the required data.
#
# To get all results for sure it's over 5000, we should use search twice based
# on author and release.
#
# First get all authors by searching email from a-z, then get all releases based
# on each author. It will make the returned result a small set.

# For example:

# First try to reach the author search, the following search URL will get all
# authors whose email starts with 'a', this will loop from 'a' to 'z.

# https://fastapi.metacpan.org/author/_search?q=email:a*&size=5000

# If we get the Author ID in above returned json, we can pass to release search
# URL as follows, it will get all releases from the passing author.

# https://fastapi.metacpan.org/release/_search?q=author:ABERNDT&size=5000


@visit_router.route(r"https://fastapi.metacpan.org/author/_search\?q=email:[a-z]\*&size=5000")
class MetaCpanAuthorURLVisitors(HttpJsonVisitor):
    """
    Run search on author's email, and parse the returned json content and form
    the MetaCpanRleaseURLVisitors' URL by adding AUTHOR condition. For example:
    https://fastapi.metacpan.org/author/_search?q=email:a*&size=5000 a* stands
    for all email which starts with 'a', and it's the same with 'A' as email is
    case insensitive. The visitor will cover all cases from a to z, and yield
    the search URLs by passing each author in the release searching URL
    """

    def get_uris(self, content):
        release_visitor_template = (
            "https://fastapi.metacpan.org/release/_search?q=author:{id}&size=5000"
        )
        hits = content.get("hits", {})
        inner_hits = hits.get("hits", [])
        for hit in inner_hits:
            _id = hit.get("_id")
            if not _id:
                continue
            yield URI(uri=release_visitor_template.format(id=_id), source_uri=self.uri)


@visit_router.route(r"https://fastapi.metacpan.org/release/_search\?q=author:\w+&size=5000")
class MetaCpanRleaseURLVisitors(HttpJsonVisitor):
    """
    Run the release results by searching the passing AUTHOR ID. The visitor will
    yield the json whose author ID is the passing author info. The
    implementation if the class is empty, it just returns for mapper use of the
    json content.
    """

    pass


@visit_router.route("http://www.cpan.org/modules/01modules.index.html")
class CpanModulesVisitors(HttpVisitor):
    """Return URIs by parsing  the HTML page of cpan modules page."""

    def get_uris(self, content):
        """
        Return the uris of authors pages, the returning URIs will be an input of
        CpanProjectHTMLVisitors
        """
        page = BeautifulSoup(content, "lxml")
        url_template = "http://www.cpan.org/{path}"
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue

            url = a["href"]
            if not url:
                continue

            if url.startswith("../authors"):
                if url.endswith((".zip", ".tar.gz")):
                    # Skip tar.gz since it will be captured by the CpanProjectHTMLVisitors
                    continue
                else:
                    url = url_template.format(path=url[3:])
                    yield URI(uri=url, source_uri=self.uri)


@visit_router.route("http://www.cpan.org/authors/.*/")
class CpanProjectHTMLVisitors(HttpVisitor):
    """
    Visit the HTML page of cpan project page and return the Packages info, HTML
    data and error.
    """

    def get_uris(self, content):
        """
        Return the uris by looking for the tar.gz in the html, and then forming
        the uri for meta and readme files
        """
        page = BeautifulSoup(content, "lxml")
        if self.uri.endswith("/"):
            url_template = self.uri + "{path}"
        else:
            url_template = self.uri + "/{path}"
        for a in page.find_all(name="a"):
            if "href" not in a.attrs:
                continue

            url = a["href"]
            if not url:
                continue

            if url.startswith(("/", "?")):
                continue  # Avoid the directory and other non-file links
            else:
                name = url
                name = name.replace("tar.gz", "").replace(".readme", "").replace(".meta", "")
                partitions = name.rpartition("-")
                name = partitions[0]
                version = partitions[-1]
                package_url = None
                if name and version:
                    package_url = PackageURL(type="cpan", name=name, version=version).to_string()
                url = url_template.format(path=url)
                yield URI(uri=url, package_url=package_url, source_uri=self.uri)


@visit_router.route("http://www.cpan.org/.*.meta")
class CpanMetaVisitors(HttpVisitor):
    """
    Visit the meta file and return the meta data of the Package The goal
    of this visitor is to get the content instead of returning any valid
    uris.
    """

    pass


@visit_router.route("http://www.cpan.org/.*.readme")
class CpanReadmeVisitors(HttpVisitor):
    """Visit the readme file and translate to json and dump it and return for mapper use."""

    def dumps(self, content):
        """Return the json by parsing the readme content"""
        # Handle bytes properly in python3
        if type(content) is bytes:
            content = content.decode("utf-8")

        lines = content.splitlines()
        readme_dict = dict()
        body = []
        head = None
        for line in lines:
            if len(line) > 1 and line.isupper() and line[0] != " ":
                if head:
                    readme_dict[head] = "\n".join(body).lstrip("\n").rstrip("\n")
                head = line
                body = []
            else:
                body.append(line.strip())
        return json.dumps(readme_dict)


@map_router.route(r"https://fastapi.metacpan.org/release/_search\?q=author:\w+&size=5000")
class MetaCpanReleaseSearchMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """Yield packages by parsing the json returned from release search request."""
        metadata = resource_uri.data
        build_packages_from_release_json(metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_release_json(metadata, uri=None):
    """
    Yield packages built from the json from release search request.
    metadata: json content with metadata
    uri: the uri of the ResourceURI object
    """
    content = json.loads(metadata)
    hits = content.get("hits", {})
    inner_hits = hits.get("hits", [])
    for hit in inner_hits:
        release = hit.get("_source", {})
        if not release:
            continue
        name = release.get("name")
        if not name:
            continue

        extracted_license_statement = [
            lic for lic in release.get("license", []) if lic and lic.strip()
        ]

        common_data = dict(
            datasource_id="cpan_release_json",
            type="cpan",
            name=name,
            description=release.get("abstract"),
            version=release.get("version"),
            download_url=release.get("download_url"),
            extracted_license_statement=extracted_license_statement,
            license_detections=[],
            # the date format passing is like:
            # "2014-04-20T21:30:13"
            release_date=parse_date(release.get("date")),
        )

        # Get the homepage_url, declared_license and vcs_repository/vcs_tool under resources section.
        # The resources section format is like this:
        # "resources" : {
        #      "homepage" : "http://plackperl.org",
        #      "license" : [
        #         "http://dev.perl.org/licenses/"
        #      ],
        #      "bugtracker" : {
        #         "web" : "https://github.com/plack/Plack/issues"
        #      },
        #      "repository" : {
        #         "url" : "git://github.com/plack/Plack.git"
        #      }
        #  },
        resources = release.get("resources") or {}

        common_data["homepage_url"] = resources.get("homepage")
        # Usually the license in root node contains the license name
        # like perl_5. The license here under resources section is the
        # url of license for example: http://dev.perl.org/licenses/ So
        # it's useful to collect both information...
        license_url = [lic for lic in resources.get("license", []) if lic and lic.strip()]
        if license_url:
            common_data["extracted_license_statement"].extend(license_url)

        vcs_tool, vcs_repo = get_vcs_repo1(resources)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + "+" + vcs_repo
        common_data["vcs_url"] = vcs_repo

        bugtracker_section = resources.get("bugtracker", {})
        common_data["bug_tracking_url"] = bugtracker_section.get("web")

        if release.get("author"):
            party = scan_models.Party(
                type=scan_models.party_person, name=release.get("author"), role="author"
            )
            common_data["parties"] = common_data.get("parties", [])
            common_data["parties"].append(party.to_dict())

        package = scan_models.Package.from_package_data(
            package_data=common_data,
            datafile_path=uri,
        )
        package_url = PackageURL(
            type="cpan", name=release.get("name"), version=release.get("version")
        )
        package.set_purl(package_url.to_string())
        yield package


def get_vcs_repo1(content):
    """Return the repo type and url."""
    repo_type = None
    repo_url = None
    repo = content.get("repository", {})
    if repo:
        url = repo.get("url")
        if url:
            repo_url = url
        if ".git" in url:
            repo_type = "git"
    return repo_type, repo_url


@map_router.route("http://www.cpan.org/.*.meta")
class CpanMetaFileMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_metafile(metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_metafile(metadata, uri=None, purl=None):
    """
    Yield Package built from Cpan a `metadata` content
    metadata: json content with metadata
    uri: the uri of the ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    # FIXME: it does not make sense to use a single function tod eal with the two
    # formats IMHO
    if is_json(metadata):
        content = json.loads(metadata)
    else:
        content = saneyaml.load(metadata)

    licenses_content = content.get("license")
    extracted_license_statement = []
    if licenses_content:
        if isinstance(licenses_content, list):
            for lic in licenses_content:
                extracted_license_statement.append(lic)
        else:
            extracted_license_statement.append(licenses_content)

    keywords_content = content.get("keywords", [])

    download_url = uri.replace(".meta", ".tar.gz") if uri else None

    name = content.get("name")
    if name:
        vcs_tool, vcs_repo = get_vcs_repo(content)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + "+" + vcs_repo
        common_data = dict(
            datasource_id="cpan_meta_json",
            type="cpan",
            name=name,
            description=content.get("abstract", name),
            version=content.get("version"),
            download_url=download_url,
            extracted_license_statement=extracted_license_statement,
            vcs_url=vcs_repo,
            keywords=keywords_content,
        )

        parties = common_data["parties"] = []

        for author_content in content.get("author", []):
            # The author format is like: Abigail <cpan@abigail.be>
            if "<" in author_content:
                author_name, _, author_email = author_content.partition("<")
                author_email = author_email.strip(">")
            else:
                author_name = author_content
                author_email = ""

            party = scan_models.Party(
                role="author",
                type=scan_models.party_person,
                name=author_name.rstrip(),
                email=author_email,
            )

            parties.append(party.to_dict())

        package = scan_models.PackageData.from_data(package_data=common_data)
        package.set_purl(purl)
        yield package


def get_vcs_repo(content):
    """Return the repo type and url."""
    repo = content.get("resources", {}).get("repository")
    if repo:
        if isinstance(repo, dict):
            repo = repo.get("url", "")
        if repo.startswith("git:"):
            return "git", repo
    return None, None


def is_json(json_content):
    try:
        json.loads(json_content)
    except ValueError:
        return False
    return True


@map_router.route("http://www.cpan.org/.*.readme")
class CpanReadmeFileMapper(Mapper):
    def get_packages(self, uri, resource_uri):
        """
        Yield Package built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        metadata = resource_uri.data
        build_packages_from_metafile(metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_readmefile(metadata, uri=None, purl=None):
    """
    Yield Package built from Cpan a `readme` content
    metadata: json metadata content of readme file
    uri: the uri of the ResourceURI object
    purl: String value of the package url of the ResourceURI object
    """
    content = json.loads(metadata)
    name = content.get("NAME")
    if name:
        download_url = uri.replace(".meta", ".tar.gz") if uri else None
        vcs_tool, vcs_repo = get_vcs_repo_fromstring(content)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + "+" + vcs_repo
        copyr = content.get("COPYRIGHT and LICENSE")
        common_data = dict(
            datasource_id="cpan_readme",
            type="cpan",
            name=name,
            description=content.get("ABSTRACT", name),
            download_url=download_url,
            vcs_url=vcs_repo,
            copyright=copyr,
            version=content.get("VERSION"),
        )

        authors = content.get("AUTHOR", [])
        for author_content in authors:
            author_split = author_content.split("<")
            if len(author_split) > 1:
                party = scan_models.Party(
                    type=scan_models.party_person,
                    name=author_split[0].rstrip(),
                    role="author",
                    email=author_split[1].replace(">", ""),
                )
                parties = common_data.get("parties")
                if not parties:
                    common_data["parties"] = []
                common_data["parties"].append(party)

        keywords_content = []
        if content.get("KEYWORDS"):
            keywords_content = [content.get("KEYWORDS")]
        common_data["keywords"] = keywords_content

        package = scan_models.PackageData.from_data(package_data=common_data)
        package.set_purl(purl)
        yield package


def get_vcs_repo_fromstring(content):
    """Return the repo type and url."""
    repo = content.get("DEVELOPMENT")
    if repo and repo.index("<") < repo.index(">") and "git:" in repo:
        return "git", repo[repo.index("<") + 1 : repo.index(">")]
    else:
        return None, None


def build_packages(release_json, purl):
    """
    Yield ScannedPackage built from MetaCPAN release API.

    Example release_json (_source):
    {
      "name": "Mojolicious-9.22",
      "distribution": "Mojolicious",
      "version": "9.22",
      "abstract": "A next-generation web framework for Perl",
      "license": ["perl_5"],
      "author": "SRI",
      "resources": {
        "homepage": "https://mojolicious.org",
        "repository": { "url": "https://github.com/mojolicious/mojo" }
      },
      "download_url": "https://cpan.metacpan.org/authors/id/S/SR/SRI/Mojolicious-9.22.tar.gz"
    }
    """
    name = release_json.get("distribution") or purl.name
    version = release_json.get("version")
    description = release_json.get("abstract")
    release_date = release_json.get("date")
    license_list = release_json.get("license", [])

    resources = release_json.get("resources", {})
    homepage_url = resources.get("homepage")
    repo = resources.get("repository", {})
    bugtracker = resources.get("bugtracker", {})

    vcs_url = None
    if repo and repo.get("url"):
        vcs_url = repo.get("url")

    parties = []
    author = release_json.get("author")
    if author:
        parties.append(scan_models.Party(name=author, role="author"))

    download_url = release_json.get("download_url")
    size = release_json.get("stat", {}).get("size")
    md5 = release_json.get("checksum_md5")
    sha256 = release_json.get("checksum_sha256")

    keywords = release_json.get("keywords") or []

    common_data = dict(
        name=name,
        version=version,
        primary_language="Perl",
        description=description,
        release_date=release_date,
        homepage_url=homepage_url,
        vcs_url=vcs_url,
        bug_tracking_url=bugtracker.get("web"),
        code_view_url=repo.get("web"),
        repository_homepage_url=f"https://metacpan.org/release/{name}",
        repository_download_url=download_url,
        api_data_url=f"https://fastapi.metacpan.org/v1/release/{name}",
        extracted_license_statement=license_list,
        declared_license_expression=" OR ".join(license_list) if license_list else None,
        parties=parties,
        keywords=keywords,
        size=size,
        md5=md5,
        sha256=sha256,
    )

    download_data = dict(
        datasource_id="cpan_pkginfo",
        type="cpan",
        download_url=download_url,
    )
    download_data.update(common_data)

    package = scan_models.PackageData.from_data(download_data)
    package.datasource_id = "cpan_api_metadata"
    package.set_purl(purl)
    yield package
