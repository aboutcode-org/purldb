#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import re
import sys

from django.db import transaction

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from discovery import mappers  # NOQA
from discovery import visitors  # NOQA

from discovery import seed
from discovery.models import ResourceURI
from discovery.management.commands import VerboseCommand


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)


class Command(VerboseCommand):
    help = ('Insert ResourceURIs records from Seed '
            'objects with a URI matching a pattern.')

    def add_arguments(self, parser):
        parser.add_argument('--pattern', '-p', action='store', dest='pattern',
                            help='Only add seed URIs matching this regex pattern.')

    def handle(self, *args, **options):
        """
        Insert seed ResourceURIs records for all the seed URIs provided
        by visitors that match a pattern.
        """
        logger.setLevel(self.get_verbosity(**options))

        pattern = options.get('pattern')
        seeders = seed.get_active_seeders()

        counter = 0
        for uri in insert_seed_uris(pattern, seeders=seeders):
            logger.info('Inserting new seed URI: {}'.format(uri))
            counter += 1
        self.stdout.write('Inserted {} seed URIs'.format(counter))


SEED_PRIORITY = 100


def insert_seed_uris(pattern=None, priority=SEED_PRIORITY, seeders=()):
    """
    Given a pattern, seed ResourceURI with new records if needed using
    the `seeders` list of Seeder instances.
    """
    with transaction.atomic():
        for seeder in seeders:
            for uri in seeder.get_seeds():
                if pattern and not re.match(pattern, uri):
                    logger.info('Skipping seeding for: {}. Pattern {}'
                                'not matched.'.format(uri, pattern))
                    continue

                if ResourceURI.objects.filter(uri=uri).exists():
                    needs_revisit = ResourceURI.objects.needs_revisit(
                        uri=uri, hours=seeder.revisit_after)
                    if not needs_revisit:
                        logger.info('Revisit not needed for: {}'.format(uri))
                        continue

                # FIXME: Currently, we update the existing a new ResourceURI
                # object with an identical `uri` value when we revisit, as the
                # ResourceURI's `data` blob may have changed. Ideally, we want
                # to store this datablob on the filesystem and have a single
                # ResourceURI per `uri` that points to one or more data blobs.
                seed_uri = ResourceURI.objects.update_or_create(
                    uri=uri,
                    priority=priority,
                    last_visit_date=None)
                assert seed_uri
                yield uri
