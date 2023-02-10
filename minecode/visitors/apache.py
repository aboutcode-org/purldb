#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from itertools import chain

from packageurl import PackageURL

from minecode import ls
from minecode import seed
from minecode import visit_router

from minecode.visitors import HttpVisitor
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import NonPersistentHttpVisitor
from minecode.visitors import URI


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
