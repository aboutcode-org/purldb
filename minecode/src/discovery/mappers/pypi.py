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

from discovery import map_router
from discovery.mappers import Mapper
from discovery.utils import parse_date


@map_router.route('https://pypi.python.org/pypi/[^/]+/[^/]+/json')
class PypiPackageMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield ScannedPackages built from resource_uri record for a single
        package version.
        Yield as many Package as there are download URLs.
        """
        # FIXME: JSON deserialization should be handled eventually by the framework
        metadata = json.loads(resource_uri.data)
        return build_packages(metadata, resource_uri.package_url)


def build_packages(metadata, purl=None):
    """
    Yield ScannedPackage built from Pypi a `metadata` mapping
    for a single package version.
    Yield as many Package as there are download URLs.

    The metadata for a Pypi package has three main blocks: info, releases and
    urls. Releases is redundant with urls and contains all download urls for
    every releases. It is repeased for each version-specific json: we ignore it
    and use only info and urls.

    purl: String value of the package url of the ResourceURI object
    """
    info = metadata['info']
    # mapping of information that are common to all the downloads of a version
    short_desc = info.get('summary')
    long_desc = info.get('description')
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = '\n'.join(descriptions)
    common_data = dict(
        name=info['name'],
        version=info['version'],
        description=description,
        homepage_url=info.get('home_page'),
        bug_tracking_url=info.get('bugtrack_url'),
    )

    author = info.get('author')
    email = info.get('author_email')
    if author or email:
        parties = common_data.get('parties')
        if not parties:
            common_data['parties'] = []
        common_data['parties'].append(scan_models.Party(
            type=scan_models.party_person, name=author, role='author', email=email))

    maintainer = info.get('maintainer')
    email = info.get('maintainer_email')
    if maintainer or email:
        parties = common_data.get('parties')
        if not parties:
            common_data['parties'] = []
        common_data['parties'].append(scan_models.Party(
            type=scan_models.party_person, name=maintainer, role='maintainer', email=email))

    declared_licenses = []
    lic = info.get('license')
    if lic and lic != 'UNKNOWN':
        declared_licenses.append(lic)

    classifiers = info.get('classifiers')
    if classifiers and not declared_licenses:
        licenses = [lic for lic in classifiers if lic.lower().startswith('license')]
        for lic in licenses:
            declared_licenses.append(lic)

    if declared_licenses:
        common_data['declared_license'] = '\n'.join(declared_licenses)

    kw = info.get('keywords')
    if kw:
        common_data['keywords'] = [k.strip() for k in kw.split(',') if k.strip()]

    # FIXME: we should either support "extra" data in a ScannedPackage or just ignore this kind of FIXME comments for now

    # FIXME: not supported in ScanCode Package: info.platform may provide some platform infor (possibly UNKNOWN)
    # FIXME: not supported in ScanCode Package: info.docs_url
    # FIXME: not supported in ScanCode Package: info.release_url "http://pypi.python.org/pypi/Django/1.10b1"
    # FIXME: not supported in ScanCode Package: info.classifiers: this contains a lot of other info (platform, license, etc)
    # FIXME: if the homepage is on Github we can infer the VCS
    # FIXME: info.requires_dist contains a list of requirements/deps that should be mapped to dependencies?
    # FIXME: info.requires_python may be useful and should be mapped to some platform?
    # FIXME: Package Index Owner: seems to be only available on the web page

    # A download_url may be provided for off Pypi download: we yield a package if relevant
    # FIXME: do not prioritize the download_url outside Pypi over actual exact Pypi donwload URL
    download_url = info.get('download_url')
    if download_url and download_url != 'UNKNOWN':
        download_data = dict(download_url=download_url)
        download_data.update(common_data)
        package = scan_models.PackageData(
            type='pypi',
            **download_data
        )
        package.set_purl(purl)
        yield package

    # yield a package for each download URL
    for download in metadata['urls']:
        url = download.get('url')
        if not url:
            continue

        download_data = dict(
            download_url=url,
            size=download.get('size'),
            release_date=parse_date(download.get('upload_time')),
        )
        # TODO: Check for other checksums
        download_data['md5'] = download.get('md5_digest')
        download_data.update(common_data)
        package = scan_models.PackageData(
            type='pypi',
            **download_data
        )
        package.set_purl(purl)
        yield package
