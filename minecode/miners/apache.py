#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from itertools import chain
import json
import logging

from commoncode import fileutils
from packageurl import PackageURL
import packagedcode.models as scan_models

from minecode import ls
from minecode import seed
from minecode import map_router
from minecode import visit_router
from minecode.miners import Mapper
from minecode.miners import HttpVisitor
from minecode.miners import HttpJsonVisitor
from minecode.miners import NonPersistentHttpVisitor
from minecode.miners import URI
from minecode.utils import parse_date


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


"""
Collect data from Apache.org.
There are two primary sources of data:

1. directory listings of the downloads distribution web site apache.org/dist
   and archive.apache.org. These map well to packages but we get little or no
   data beside a checksum and some name and painfully extracted version.
   This data could also be fetched for the most recent ones (since 2012) from:
   https://dist.apache.org/repos/dist/release/ which is an SVN repo
   And svn ls -R https://dist.apache.org/repos/dist/release/ could be more
   efficient and easier to parse incrementally?

2. JSON data collated by the Foundation to provide project information. These
   are for projects and do not map very well to a package or download (but
   rather to several of thems at once)

The JSON data comes from https://projects.apache.org/about.html and
is created with this code:
https://svn.apache.org/repos/asf/comdev/projects.apache.org/trunk/ .

This JSON data is project-level except for releases-files.json .. but this is
just based on parsing the find-ls directory listing so bring nothing new.

- http://home.apache.org/public/public_ldap_projects.json : seems to be the
  origin for the projects.json and podlings.json data

- These is a list of VCS repositories. Each key maps rather well to a package
  name. But the key (some package name?) may not match a project:
  https://projects.apache.org/json/foundation/repositories.json
  This comes from http://git.apache.org/

- This more or less maps to top-level projects but does not relate to packages
  https://projects.apache.org/json/foundation/committees.json

- This list podling projects with only few details and does not map to packages
  https://projects.apache.org/json/foundation/podlings.json

- This should contain an entry for each project but does not. Yet each JSON
  contains also the releases.json and repositories.json content for that project.
  https://projects.apache.org/json/projects/

- This seems to be the origin of most project data:
  https://svn.apache.org/repos/asf/comdev/projects.apache.org/trunk/data/projects.xml

- Another source of the JSON may be:
  https://whimsy.apache.org/public/
"""


class ApacheSeed(seed.Seeder):

    def get_seeds(self):
        # note: this is the same as below and does not list archived files
        # https://archive.apache.org/dist/zzz/find-ls.gz
        # to get these we need to rsync or use other techniques
        yield 'https://apache.org/dist/zzz/find-ls.gz'

        # FIXME: we cannot relate this to a download  package: disabled for now
        # yield 'https://projects.apache.org/json/foundation/projects.json'
        # yield 'https://projects.apache.org/json/foundation/podlings.json'


CHECKSUM_EXTS = '.sha256', '.sha512', '.md5', '.sha', '.sha1',

# only keep downloads with certain extensions for some archives, packages and checksums
ARCHIVE_EXTS = (
    # archives
    '.jar', '.zip', '.tar.gz', '.tgz', '.tar.bz2', '.war', '.tar.xz', '.tgz', '.tar',
    # packages
    # '.deb', '.rpm', '.msi', '.exe',
    '.whl', '.gem', '.nupkg',
    # '.dmg',
    # '.nbm',
)

IGNORED_PATH_CONTAINS = (
    'META/',  # #
    # doc
    '/documentation/',
    '/doc/',  # #
    '-doc.',  # #
    '-doc-',  # #

    '/docs/',  # #
    '-docs.',  # #
    '-docs-',  # #

    'javadoc',  # #
    'fulldoc',  # #
    'apidoc',  # #
    '-manual.',
    '-asdocs.',  # #

    # eclipse p2/update sites are redundant
    # redundant
    'updatesite/',  # #
    'eclipse-update-site',  # #
    'update/eclipse',  # #
    'sling/eclipse',  # #
    'eclipse.site-',

    # large multi-origin binary distributions
    '-distro.',
    '-bin-withdeps.',
    '-bin-with-deps',

    # these are larger distributions with third-parties
    'apache-airavata-distribution',
    'apache-airavata-server',
    'apache-mahout-distribution',
    '/syncope-standalone-',

    'binaries/conda',

    # obscure
    'perl/contrib',
    # index data
    'zzz',
    # doc
    'ant/manual'
)


# TODO: ignore these globs too:

# openoffice/*/binaries is very large
# /*/apache-log4j-*-site.zip


SOURCE_INDICATORS = (
    '_src.',
    '-src.',
    '-source.',
    '-sources.',
    '-source-release',
    '/source/',
    '/sources/',
    '/src/',
    '_sources.',
)


BINARY_INDICATORS = (
)


@visit_router.route('https?://apache.org/dist/zzz/find\-ls\.gz')
class ApacheDistIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect URIs for all packages in the "find -ls" index available from Apache
    dist sites.
    """
    def get_uris(self, content):
        import gzip
        with gzip.open(content, 'rt') as f:
            content = f.read()

        url_template = 'https://apache.org/dist/{path}'

        archive_checksum_extensions = tuple(chain.from_iterable(
            [[ae + cke for ae in ARCHIVE_EXTS] for cke in CHECKSUM_EXTS]))
        kept_extensions = archive_checksum_extensions + ARCHIVE_EXTS

        for entry in ls.parse_directory_listing(content, from_find=True):
            # skip directories, links and special files
            if entry.type != ls.FILE:
                continue
            path = entry.path

            # ignore several downloads
            if (not path.endswith(kept_extensions)
                    or any(i in path for i in IGNORED_PATH_CONTAINS)):
                continue
            # only checksums need further visit, the archive will be scanned only
            is_visited = not path.endswith(CHECKSUM_EXTS)

            yield URI(
                visited=is_visited,
                source_uri=self.uri,
                uri=url_template.format(path=path),
                package_url=build_purl(path),
                size=entry.size
            )


def build_purl(uri):
    """
    Return a PackageURL built from an Apache download URL or path.

    URLs start with this prefix 'https://apache.org/dist/'
    """
    # FIXME: this is the essence of collecting name and versions for Apache and
    # this need to be super robust
    segments = [p for p in uri.split('/') if p]
    version = None
    project_name = segments[0]
    # The path typically contains the version but where is highly inconsistent
    # - bahir/bahir-spark/2.1.1/apache-bahir-2.1.1-src.zip
    # - groovy/2.4.15/sources/apache-groovy-src-2.4.15.zip
    # FIXME: this is not correct
    if len(segments) > 1 and ('/distribution/' in uri or '/sources/' in uri):
        version = segments[1]

    package_url = PackageURL(
        type='apache',
        # TODO: namespace='',
        name=project_name,
        version=version)

    return package_url


@visit_router.route('https?://(archive\.)apache.org/dist/.*\.(md5|sha1?|sha256|sha512)',)
class ApacheChecksumVisitor(HttpVisitor):
    """
    Collect files that contain archive checksums.
    """
    def dumps(self, content):
        if content:
            # the format can be md5sum-like this way:
            # c7a2d3becea1d28b518528f8204b8d2a  apache-groovy-docs-2.4.6.zip
            # with split on space to get the checksum value.
            content = content.split()
            if content:
                content = content[0]
            else:
                content = ''
            return content


# FIXME: we cannot relate this to a download  package: disabled for now
# @visit_router.route('https://projects.apache.org/json/foundation/projects.json')
class ApacheProjectsJsonVisitor(HttpJsonVisitor):
    """
    Collect URIs for all Apache projects.

    The json format is like:
        "abdera": {
            "bug-database": "https://issues.apache.org/jira/browse/ABDERA",
            "category": "xml",
            "created": "2008-12-25",
            "description": "The goal of the Apache Abdera project ....",
            "doap": "http://svn.apache.org/repos/asf/abdera/java/trunk/doap_Abdera.rdf",
            "download-page": "http://abdera.apache.org/#downloads",
            "homepage": "http://abdera.apache.org",
            "license": "http://usefulinc.com/doap/licenses/asl20",
            "mailing-list": "http://abdera.apache.org/project.html#lists",
            "name": "Apache Abdera",
            "pmc": "abdera",
            "programming-language": "Java",
            "release": [
            {
            "created": "2008-04-11",
            "name": "Apache Abdera 0.4",
            "revision": "1.7.1"
            }
            ],
            "repository": [
            "http://svn.apache.org/repos/asf/abdera"
            ],
            "shortdesc": "An open source Atom implementation"
        },
    """
    def get_uris(self, content):
        url_template = 'https://projects.apache.org/json/projects/{name}.json'
        for project_name, project_meta in content.items():
            package_url = PackageURL(type='apache', name=project_name)
            yield URI(
                uri=url_template.format(name=project_name),
                package_url=package_url.to_string(),
                date=project_meta.get('created'))


# FIXME: we cannot relate this to a download  package: disabled for now
# @visit_router.route('https://projects.apache.org/json/projects/.*json')
class ApacheSingleProjectJsonVisitor(HttpJsonVisitor):
    """
    Collect json content from single project json file. It does not
    return any URI as the json contains the project meatadata only, so
    this visitor is getting the json to pass to mapper.
    """
    pass


# FIXME: what can we do with a homepage and nam, packagedb wise??
# @visit_router.route('https://projects.apache.org/json/foundation/podlings.json')
class ApachePodlingsJsonVisitor(HttpJsonVisitor):
    """
    Collect name and homepage for all podlings aka "incubator" projects.

    The json format is like:
        "airflow": {
        "description": "Airflow is a workflow automation and scheduling ...",
        "homepage": "http://airflow.incubator.apache.org/",
        "name": "Apache Airflow (Incubating)",
        "pmc": "incubator",
        "podling": true,
        "started": "2016-03"
        },
    """
    def get_uris(self, content):
        for project_name, project_meta in content.items():
            if 'homepage' not in project_meta:
                continue

            package_url = PackageURL(
                type='apache',
                namespace='incubator',
                name=project_name)

            yield URI(
                uri=project_meta.get('homepage'),
                package_url=package_url.to_string(),
                data=project_meta,
                source_uri=self.uri,
                visited=True)


# common licenses found in JSON
APACHE_LICENSE_URL = {
    'http://usefulinc.com/doap/licenses/asl20',
    'https://usefulinc.com/doap/licenses/asl20',
    'http://spdx.org/licenses/Apache-2.0',
    'https://spdx.org/licenses/Apache-2.0',
    'http://www.apache.org/licenses/LICENSE-2.0',
    'https://www.apache.org/licenses/LICENSE-2.0',
    'http://www.apache.org/licenses/LICENSE-2.0.txt',
    'https://www.apache.org/licenses/LICENSE-2.0.txt',
    'http://www.apache.org/licenses/',
    'http://forrest.apache.org/license.html',
    'https://svn.apache.org/repos/asf/tomee/tomee/trunk/LICENSE',
}


# FIXME: this is NOT specific to a download URL but to a project: disabled for now
# @map_router.route('https://projects.apache.org/json/foundation/projects.json')
class ApacheProjectJsonMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages built from resource_uri record for a single
        package version.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages_from_projects(metadata, uri=uri)


def build_packages_from_projects(metadata, uri=None):
    """
    Yield Package built from Apache a `metadata` mapping
    which is a dictionary keyed by project name and values are project_metadata.
    Yield as many Package as there are download URLs.
    """
    for project_name, project_meta in metadata.items():
        short_desc = project_meta.get('shortdesc')
        long_desc = project_meta.get('description')
        descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
        description = '\n'.join(descriptions)
        common_data = dict(
            datasource_id="apache_json",
            type='apache',
            name=project_name,
            description=description,
            homepage_url=project_meta.get('homepage'),
            bug_tracking_url=project_meta.get('bug-database'),
            primary_language=project_meta.get('programming-language'),
        )

        # FIXME: setting the download-page as the download_url is not right
        if project_meta.get('download-page'):
            download_url = project_meta.get('download-page')
            common_data['download_url'] = download_url
        for repo in project_meta.get('repository', []):
            common_data['code_view_url'] = repo
            # Package code_view_url only support one URL, so break when
            # finding a code_view_url
            break

        maintainers = project_meta.get('maintainer', [])
        for maintainer in maintainers:
            mailbox = maintainer.get('mbox', '').replace('mailto:', '')
            name = maintainer.get('name')
            party = scan_models.Party(type=scan_models.party_person, name=name, role='maintainer', email=mailbox)
            parties = common_data.get('parties')
            if not parties:
                common_data['parties'] = []
            common_data['parties'].append(party.to_dict())

        # license is just a URL in the json file, for example:
        # http://usefulinc.com/doap/licenses/asl20
        license_url = project_meta.get('license')
        common_data['extracted_license_statement'] = license_url

        if license_url in APACHE_LICENSE_URL:
            common_data['declared_license_expression'] = 'apache-2.0'
            common_data['declared_license_expression_spdx'] = 'Apache-2.0'
            common_data['license_detections'] = []

        keywords = []
        category = project_meta.get('category', '')
        for kw in category.split(','):
            kw = kw.strip()
            if kw:
                keywords.append(kw)
        common_data['keywords'] = keywords

        common_data['primary_language'] = project_meta.get('programming-language')

        # FIXME: these cannot be related to actual packages with a download URL
        releases = project_meta.get('release')
        if releases:
            for release in releases:
                rdata = dict(common_data)
                rdata['version'] = release.get('revision')
                if release.get('created') and len(release.get('created')) == 10:
                    rdata['release_date'] = parse_date(release.get('created'))
                else:
                    logger.warn('Unexpected date format for release date: {}'.format(release.get('created')))
                package = scan_models.Package.from_package_data(
                    package_data=rdata,
                    datafile_path=uri,
                )
                yield package
        else:
            package = scan_models.Package.from_package_data(
                    package_data=common_data,
                    datafile_path=uri,
                )
            yield package


# FIXME: this is NOT specific to a download URL but to a project: disabled for now
# FIXME: this is casting too wide a net!
# @map_router.route('http?://[\w\-\.]+.incubator.apache.org/"')
class ApachePodlingsMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages built from resource_uri record for a single
        package version.
        """
        metadata = json.loads(resource_uri.data)
        return build_packages_from_podlings(metadata, resource_uri.package_url)


def build_packages_from_podlings(metadata, purl):
    """
    Yield Package built from Apache podlings metadata
    which is a dictionary keyed by project name and values are project_metadata.
    Yield as many Package as there are download URLs.
    """
    name = metadata.get('name')
    if name:
        common_data = dict(
            type='apache-podling',
            name=name,
            description=metadata.get('description'),
            homepage_url=metadata.get('homepage'),
        )
        package = scan_models.Package(**common_data)
        package.set_purl(purl)
        yield package


@map_router.route('http?s://(archive\.)?apache\.org/dist/.*')
class ApacheDownloadMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages build from a bare download URI or download checksum URI.
        """
        if uri.endswith(CHECKSUM_EXTS):
            # 1. create a regular package from the URL stripped from its checksum extension
            archive_uri, _, checksum_type = uri.rpartition('.')

            pack = build_package_from_download(archive_uri, resource_uri.package_url)
            # 2. collect the checksum inside the file
            # and attach it to the package
            checksum_value = resource_uri.data.strip()
            if checksum_value:
                checksum_field_name = 'download_{checksum_type}'.format(**locals())
                setattr(pack, checksum_field_name, checksum_value)
                yield pack
        else:
            # a plain download URI
            yield build_package_from_download(uri, resource_uri.package_url)


def build_package_from_download(uri, purl=None):
    """
    Return a Package built from an Apache dist download archive URL.

    The uri could be:
    http://archive.apache.org/dist/groovy/2.4.6/sources/apache-groovy-src-2.4.6.zip
    https://apache.org/dist/chemistry/opencmis/1.1.0/chemistry-opencmis-dist-1.1.0-server-webapps.zip
    """
    name, version = get_name_version(uri)
    if purl:
        purl = PackageURL.from_string(purl)
        if not name:
            name = purl.name
    # FIXME: use purl data??
    package = scan_models.Package(
        type='apache',
        namespace=purl.namespace,
        name=name,
        version=version,
        download_url=uri,
    )
    package.set_purl(purl)
    return package


# FIXME: there should be only one such method and this one is rather weak
def get_name_version(uri):
    """
    Return name and version extracted from a path.
    """
    # base_url will end being 'https://archive.apache.org/dist' or  'https://apache.org/dist'
    # path is the uri without base url, for example:
    # /groovy/2.4.6/sources/apache-groovy-src-2.4.6.zip
    _, _, path = uri.partition('apache.org/dist/')
    base_name = fileutils.file_base_name(path)
    version = None
    package_name = ''
    name_segments = base_name.split('-')
    for segment in name_segments:
        try:
            # To test if each split segment with . is integer.
            # For example in '1.2.3' all chars are integer or period.
            # If so, this segment is a version segment.
            if version:
                # The segment after integer segment should belong to version too.
                # For example: turbine-4.0-M1, after detecting 4.0,
                # M1 should be including in version too, so the final version is 4.0-M1
                version = '-'.join([version, segment])
                continue

            is_all_int = all(n.isdigit() for n in segment.split('.'))
            if is_all_int:
                version = segment
        except ValueError:
            # Connect the package_name with - because we split it with - eariler, util
            # when we meet version, package_name should be good.
            if not package_name:
                package_name = segment
            else:
                package_name = ('-').join([package_name, segment])
            continue
    return package_name, version
