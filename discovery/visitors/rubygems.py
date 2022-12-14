# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import gzip
import json
import logging
import os

from rubymarshal import reader
from rubymarshal.classes import UsrMarshal
from packageurl import PackageURL

from discovery import seed
from discovery import visit_router
from discovery.utils import extract_file
from discovery.visitors import HttpJsonVisitor
from discovery.visitors import NonPersistentHttpVisitor
from discovery.visitors import URI


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# FIXME: we are missing several API calls:
# http://guides.rubygems.org/rubygems-org-api/

class RubyGemsSeed(seed.Seeder):

    def get_seeds(self):
        # We keep only specs.4.8.gz and exclude latest_spec.4.8.gz,
        # since specs.4.8.gz covers all uris in latest spec.
        yield 'http://rubygems.org/specs.4.8.gz'


class GemVersion(UsrMarshal):

    def version(self):
        return self.values['version']


@visit_router.route('https?://rubygems\.org/specs\.4\.8\.gz')
class RubyGemsIndexVisitor(NonPersistentHttpVisitor):
    """
    Collect REST APIs URIs from RubyGems index file.
    """

    def get_uris(self, content):
        with gzip.open(content, 'rb') as idx:
            index = idx.read()

        # TODO: use a purl!!!
        for name, version, platform in reader.loads(index):
            json_url = 'https://rubygems.org/api/v1/versions/{name}.json'.format(
                **locals())

            package_url = PackageURL(type='gem', name=name).to_string()
            yield URI(uri=json_url, package_url=package_url, source_uri=self.uri)

            # note: this list only has ever a single value
            version = version.values[0]
            if isinstance(version, bytes):
                version = version.decode('utf-8')

            download_url = 'https://rubygems.org/downloads/{name}-{version}'

            if isinstance(platform, bytes):
                platform = platform.decode('utf-8')
            if platform != 'ruby':
                download_url += '-{platform}'

            download_url += '.gem'
            download_url = download_url.format(**locals())
            package_url = PackageURL(type='gem', name=name, version=version).to_string()
            yield URI(uri=download_url, package_url=package_url, source_uri=self.uri)


@visit_router.route('https?://rubygems\.org/api/v1/versions/[\w\-\.]+.json')
class RubyGemsApiManyVersionsVisitor(HttpJsonVisitor):
    """
    Collect the json content of each version.
    Yield the uri of each gem based on name, platform and version.
    The data of the uri is the JSON subset for a single version.
    """

    def get_uris(self, content):
        """
        Yield URI of the gems url and data.
        """
        # FIXME: return actual data too!!!
        for version_details in content:
            # get the gems name by parsing from the uri
            name = self.uri[
                self.uri.index('/versions/') + len('/versions/'):-len('.json')]
            version = version_details.get('number')
            gem_name = '%(name)s-%(version)s' % locals()
            package_url = PackageURL(type='gem', name=name, version=version).to_string()
            download_url = 'https://rubygems.org/downloads/%(gem_name)s.gem' % locals()
            yield URI(uri=download_url, source_uri=self.uri, package_url=package_url,
                      data=json.dumps(version_details))

# TODO: add API dependencies
# https://rubygems.org/api/v1/dependencies.json?gems=file_validators
# Also use Use the V2 API at http://guides.rubygems.org/rubygems-org-api-v2/
# GET - /api/v2/rubygems/[GEM NAME]/versions/[VERSION NUMBER].(json|yaml)


@visit_router.route('https?://rubygems.org/downloads/[\w\-\.]+.gem')
class RubyGemsPackageArchiveMetadataVisitor(NonPersistentHttpVisitor):
    """
    Fetch a Rubygems gem archive, extract it and return its metadata file content.
    """

    def dumps(self, content):
        return get_gem_metadata(content)


def get_gem_metadata(location):
    """
    Return the metadata file content as a string extracted from the gem archive
    at `location`.
    """
    # Extract the compressed file first.
    extracted_location = extract_file(location)
    metadata_gz = os.path.join(extracted_location, 'metadata.gz')
    # Extract the embedded metadata gz file
    extract_parent_location = extract_file(metadata_gz)
    # Get the first file in the etracted folder which is the meta file location
    meta_extracted_file = os.path.join(extract_parent_location, os.listdir(extract_parent_location)[0])
    with open(meta_extracted_file) as meta_file:
        return meta_file.read()
