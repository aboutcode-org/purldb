#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import OrderedDict
import json

import packagedcode.models as scan_models
import saneyaml
from packageurl import PackageURL

from minecode import map_router
from minecode.mappers import Mapper
from minecode.utils import parse_date


@map_router.route('https://fastapi.metacpan.org/release/_search\?q=author:\w+&size=5000')
class MetaCpanReleaseSearchMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield packages by parsing the json returned from release search request.
        """
        metadata = resource_uri.data
        build_packages_from_release_json(metadata, resource_uri.uri, resource_uri.package_url)


def build_packages_from_release_json(metadata, uri=None):
    """
    Yield packages built from the json from release search request.
    metadata: json content with metadata
    uri: the uri of the ResourceURI object
    """
    content = json.loads(metadata)
    hits = content.get('hits', {})
    inner_hits = hits.get('hits', [])
    for hit in inner_hits:
        release = hit.get('_source', {})
        if not release:
            continue
        name = release.get('name')
        if not name:
            continue

        extracted_license_statement = [l for l in release.get('license', []) if l and l.strip()]

        common_data = dict(
            datasource_id="cpan_release_json",
            type='cpan',
            name=name,
            description=release.get('abstract'),
            version=release.get('version'),
            download_url=release.get('download_url'),
            extracted_license_statement=extracted_license_statement,
            license_detections=[],
            # the date format passing is like:
            # "2014-04-20T21:30:13"
            release_date=parse_date(release.get('date')),
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
        resources = release.get('resources') or {}

        common_data['homepage_url'] = resources.get('homepage')
        # Usually the license in root node contains the license name
        # like perl_5. The license here under resources section is the
        # url of license for example: http://dev.perl.org/licenses/ So
        # it's useful to collect both information...
        license_url = [l for l in resources.get('license', []) if l and l.strip()]
        if license_url:
            common_data['extracted_license_statement'].extend(license_url)

        vcs_tool, vcs_repo = get_vcs_repo1(resources)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + '+' + vcs_repo
        common_data['vcs_url'] = vcs_repo

        bugtracker_section = resources.get('bugtracker', {})
        common_data['bug_tracking_url'] = bugtracker_section.get('web')

        if release.get('author'):
            party = scan_models.Party(
                type=scan_models.party_person,
                name=release.get('author'), role='author')
            common_data['parties'] = common_data.get('parties', [])
            common_data['parties'].append(party.to_dict())

        package = scan_models.Package.from_package_data(
            package_data=common_data,
            datafile_path=uri,
        )
        package_url = PackageURL(type='cpan', name=release.get('name'), version=release.get('version'))
        package.set_purl(package_url.to_string())
        yield package


def get_vcs_repo1(content):
    """
    Return the repo type and url.
    """
    repo_type = None
    repo_url = None
    repo = content.get('repository', {})
    if repo:
        url = repo.get('url')
        if url:
            repo_url = url
        if '.git' in url:
            repo_type = 'git'
    return repo_type, repo_url


@map_router.route('http://www.cpan.org/.*.meta')
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
    # FIXME: it does not make sense to use a single functin tod eal with the two
    # formats IMHO
    if is_json(metadata):
        content = json.loads(metadata, object_pairs_hook=OrderedDict)
    else:
        content = saneyaml.load(metadata)

    licenses_content = content.get('license')
    extracted_license_statement = []
    if licenses_content:
        if isinstance(licenses_content, (list,)):
            for lic in licenses_content:
                extracted_license_statement.append(lic)
        else:
            extracted_license_statement.append(licenses_content)

    keywords_content = content.get('keywords', [])

    download_url = uri.replace('.meta', '.tar.gz') if uri else None

    name = content.get('name')
    if name:
        vcs_tool, vcs_repo = get_vcs_repo(content)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + '+' + vcs_repo
        common_data = dict(
            datasource_id="cpan_metadata_json",
            type='cpan',
            name=name,
            description=content.get('abstract', name),
            version=content.get('version'),
            download_url=download_url,
            extracted_license_statement=extracted_license_statement,
            vcs_url=vcs_repo,
            keywords=keywords_content,
        )

        parties = common_data['parties'] = []

        for author_content in content.get('author', []):
            # The author format is like: Abigail <cpan@abigail.be>
            if '<' in author_content:
                author_name, _, author_email = author_content.partition('<')
                author_email = author_email.strip('>')
            else:
                author_name = author_content
                author_email = ''

            party = scan_models.Party(
                role='author',
                type=scan_models.party_person,
                name=author_name.rstrip(),
                email=author_email
            )

            parties.append(party.to_dict())

        package = scan_models.PackageData.from_data(package_data=common_data)
        package.set_purl(purl)
        yield package


def get_vcs_repo(content):
    """
    Return the repo type and url.
    """
    repo = content.get('resources', {}).get('repository')
    if repo:
        if isinstance(repo, dict):
            repo = repo.get('url', '')
        if repo.startswith('git:'):
            return 'git', repo
    return None, None


def is_json(json_content):
    try:
        json.loads(json_content)
    except ValueError:
        return False
    return True


@map_router.route('http://www.cpan.org/.*.readme')
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
    name = content.get('NAME')
    if name:
        download_url = uri.replace('.meta', '.tar.gz') if uri else None
        vcs_tool, vcs_repo = get_vcs_repo_fromstring(content)
        if vcs_tool and vcs_repo:
            # Form the vsc_url by
            # https://spdx.org/spdx-specification-21-web-version#h.49x2ik5
            vcs_repo = vcs_tool + '+' + vcs_repo
        copyr = content.get('COPYRIGHT and LICENSE')
        common_data = dict(
            datasource_id="cpan_readme",
            type='cpan',
            name=name,
            description=content.get('ABSTRACT', name),
            download_url=download_url,
            vcs_url=vcs_repo,
            copyright=copyr,
            version=content.get('VERSION')
        )

        authors = content.get('AUTHOR', [])
        for author_content in authors:
            author_split = author_content.split('<')
            if len(author_split) > 1:
                party = scan_models.Party(type=scan_models.party_person, name=author_split[0].rstrip(), role='author', email=author_split[1].replace('>', ''))
                parties = common_data.get('parties')
                if not parties:
                    common_data['parties'] = []
                common_data['parties'].append(party)

        keywords_content = []
        if content.get('KEYWORDS'):
            keywords_content = [content.get('KEYWORDS')]
        common_data['keywords'] = keywords_content

        package = scan_models.PackageData.from_data(package_data=common_data)
        package.set_purl(purl)
        yield package


def get_vcs_repo_fromstring(content):
    """
    Return the repo type and url.
    """
    repo = content.get('DEVELOPMENT')
    if repo and repo.index('<') < repo.index('>') and 'git:' in repo:
        return 'git', repo[repo.index('<') + 1: repo.index('>')]
    else:
        return None, None
