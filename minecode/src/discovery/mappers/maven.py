#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json
import logging
import packageurl
from packageurl import PackageURL

from commoncode.text import as_unicode
from packagedcode.models import PackageData
from packagedcode.maven import _parse

from discovery import map_router
from discovery.mappers import Mapper
from discovery.utils import parse_date
from discovery.visitors.maven import Artifact


TRACE = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


if TRACE:
    import sys
    logging.basicConfig(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)


@map_router.route('maven-index://.*')
class MavenIndexArtifactMapper(Mapper):
    """
    Process the minimal artifacts collected for a Maven Jar or POM in an
    index visit.
    """

    def get_packages(self, uri, resource_uri):
        yield get_mini_package(resource_uri.data, uri, resource_uri.package_url)


def get_mini_package(data, uri, purl):
    """
    Return a MavenPomPackage built from the minimal artifact data available in a
    nexus index, given a `data` JSON string, a `uri` string and a `purl`
    PacxkageURL string. Return None if the package cannot be built.
    """
    if not data:
        return

    artdata = json.loads(data)

    # FIXME: this should a slot in Artifact
    download_url = artdata.pop('download_url')
    # FIXME: what if this is an ArtifactExtended??
    artifact = Artifact(**artdata)

    if purl:
        if isinstance(purl, str):
            purl = PackageURL.from_string(purl)
        assert isinstance(purl, PackageURL)

    qualifiers = None
    if purl and purl.qualifiers:
        qualifiers = packageurl.normalize_qualifiers(purl.qualifiers, encode=False)
    if qualifiers:
        assert isinstance(qualifiers, dict)
    logger.debug('get_mini_package: qualifiers: {}'.format(qualifiers))

    package = PackageData(
        type='maven',
        namespace=artifact.group_id,
        name=artifact.artifact_id,
        version=artifact.version,
        qualifiers=qualifiers,
        description=artifact.description,
        download_url=download_url,
        release_date=parse_date(artifact.last_modified),
        size=artifact.size,
        sha1=artifact.sha1 or None,
    )
    logger.debug('get_mini_package: package.qualifiers: {}'.format(package.qualifiers))
    logger.debug('get_mini_package for uri: {}, package: {}'.format(uri, package))
    return package


# FIXME this should be valid for any POM
@map_router.route('https?://repo1.maven.org/maven2/.*\.pom')
class MavenPomMapper(Mapper):
    """
    Map a proper full POM visited as XML.
    """
    def get_packages(self, uri, resource_uri):

        logger.debug('MavenPomMapper.get_packages: uri: {}, resource_uri: {}, purl:'
                     .format(uri, resource_uri.uri, resource_uri.package_url))
        package = get_package(resource_uri.data, resource_uri.package_url)
        if package:
            logger.debug('MavenPomMapper.get_packages: uri: {}, package: {}'
                         .format(uri, package))
            yield package


def get_package(text, package_url=None,
                baseurl='https://repo1.maven.org/maven2'):
    """
    Return a ScannedPackage built from a POM XML string `text`.
    """
    text = as_unicode(text)
    package = _parse(
        datasource_id='maven_pom',
        package_type='maven',
        primary_language='Java',
        text=text
    )
    if package:
        # FIXME: this should be part of the parse call
        if package_url:
            purl = PackageURL.from_string(package_url)
            package.set_purl(purl)
        # Build proper download_url given a POM: this must be the URL for
        # the Jar which is the key to the PackageDB record
        # FIXME the download is hardcoded to Maven Central?
        # package.download_url = package.repository_download_url(baseurl=baseurl)
    return package
