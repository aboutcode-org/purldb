#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import json

from packageurl import PackageURL

from packagedcode.npm import npm_api_url
from packagedcode.npm import split_scoped_package_name

from discovery import seed
from discovery import visit_router
from discovery.visitors import NonPersistentHttpVisitor
from discovery.visitors import URI


"""
Collect NPM packages from npm registries.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class NpmSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=1000&since=0'


@visit_router.route('https://replicate.npmjs.com/registry/_changes\?include_docs=true&limit=\d+&since=\d+')
class NpmRegistryVisitor(NonPersistentHttpVisitor):
    """
    Yield one URI for the next batch of changes to re-visit. Yield one URI for
    each NPM package (that contains all the versions for this package) as
    previsited for mapping.
    """
    def get_uris(self, content):
        """
        Yield a URI for the next index sequence to visit and one URI for each
        package fetched in a batch.
        """
        next_visitable_index_url_template = (
            'https://replicate.npmjs.com/registry/_changes?include_docs=true&limit=1000&since={last_seq}')

        json_location = content
        with open(json_location) as c:
            content = json.loads(c.read())

        try:
            last_seq = content['last_seq']
        except KeyError:
            # provide a more meaningful message in case the JSON is incorrect
            raise Exception('NpmRegistryVisitor: Missing "last_seq" field: Aborting.')

        # Always yield an index URI, even if there is no results to avoid stopping the index visits
        yield URI(uri=next_visitable_index_url_template.format(last_seq=last_seq), source_uri=self.uri)

        try:
            results = content['results']
        except KeyError:
            # provide a more meaningful message in case the JSON is incorrect
            raise Exception(
                'NpmRegistryVisitor: Missing "results" field: Aborting.')

        for result in results:
            doc = result.get('doc')
            # verify if this record is a package record (as opposed to
            # some couchdb design document that we would ignore)
            is_package_record = 'versions' in doc and 'name' in doc
            if not is_package_record:
                continue

            # remove the readme field from the data: this is big and mostly
            # useless for now
            doc.pop('readme', None)

            name = doc.get('name')

            namespace, name = split_scoped_package_name(name)
            package_api_url = npm_api_url(namespace, name)

            package_url = PackageURL(
                type='npm',
                namespace=namespace,
                name=name).to_string()

            # here: this is ready for mapping
            yield URI(
                uri=package_api_url,
                package_url=package_url,
                source_uri=self.uri,
                data=json.dumps(doc, separators=(',', ':'), ensure_ascii=False),
                # note: visited is True since there nothing more to visit
                visited=True)
