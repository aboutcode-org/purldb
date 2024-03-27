#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from packagedcode import models as scan_models

from minecode import map_router
from minecode.mappers import Mapper


@map_router.route('https://storage.googleapis.com/google-code-archive/v2/code.google.com/.*/project.json')
class GoogleNewAPIV2ProjectJsonMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages built from resource_uri record for a single
        package version.
        """
        # FIXME: JSON deserialization should be handled eventually by the
        # framework
        metadata = json.loads(resource_uri.data)
        return build_packages_from_projectsjson_v2(metadata, resource_uri.package_url, uri)


def build_packages_from_projectsjson_v2(metadata, purl=None, uri=None):
    """
    Yield Package built from Googlecode API json `metadata` mapping
    which is a dictionary keyed by project name and values are metadatadata.
    Yield as many Package as there are download URLs.
    metadata: json metadata content from API call
    purl: String value of the package url of the ResourceURI object
    """
    short_desc = metadata.get('summary')
    long_desc = metadata.get('description')
    descriptions = [d for d in (short_desc, long_desc) if d and d.strip()]
    description = '\n'.join(descriptions)
    common_data = dict(
        datasource_id='googlecode_api_json',
        type='googlecode',
        name=metadata.get('name'),
        description=description
    )

    license_name = metadata.get('license')
    if license_name:
        common_data['extracted_license_statement'] = license_name

    keywords = []
    labels = metadata.get('labels')
    for label in labels:
        if label:
            keywords.append(label.strip())
    common_data['keywords'] = keywords

    package = scan_models.Package.from_package_data(
        package_data=common_data,
        datafile_path=uri,
    )
    package.set_purl(purl)
    yield package


@map_router.route('https://www.googleapis.com/storage/v1/b/google-code-archive/o/v2.*project.json\?alt=media')
class GoogleNewAPIV1ProjectJsonMapper(Mapper):

    def get_packages(self, uri, resource_uri):
        """
        Yield Packages built from resource_uri record for a single
        package version.
        """
        # FIXME: JSON deserialization should be handled eventually by the
        # framework
        metadata = json.loads(resource_uri.data)
        return build_packages_from_projectsjson_v1(metadata, resource_uri.package_url, uri)


def build_packages_from_projectsjson_v1(metadata, purl=None, uri=None):
    """Yield Package from the project.json passed by the google code v1 API
    metadata: json metadata content from API call
    purl: String value of the package url of the ResourceURI object
    """
    if metadata.get('name'):
        common_data = dict(
            datasource_id="googlecode_json",
            type='googlecode',
            name=metadata.get('name'),
            description=metadata.get('description')
        )

        license_name = metadata.get('license')
        if license_name:
            common_data['extracted_license_statement'] = license_name

        keywords = []
        labels = metadata.get('labels')
        for label in labels:
            if label:
                keywords.append(label.strip())
        common_data['keywords'] = keywords

        common_data['vcs_url'] = metadata.get('ancestorRepo')
        common_data['namespace'] = metadata.get('domain')

        # createTime doesn't make sense since the timestamp value is incorrect
        # and parsing it will give a wrong year out of range.

        # created_time = metadata.get('creationTime')
        # if created_time:
        #    common_data['release_date'] = date.fromtimestamp(created_time)
        package = scan_models.Package.from_package_data(
            package_data=common_data,
            datafile_path=uri,
        )
        package.set_purl(purl)
        yield package
