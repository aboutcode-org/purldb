#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from datetime import timedelta
import os
from io import StringIO

from django.core import management
from django.utils import timezone
from mock import patch

from discovery.management.commands.seed import SEED_PRIORITY
from discovery.management.commands.seed import insert_seed_uris
from discovery.models import ResourceURI
from discovery import seed
from discovery.utils_test import MiningTestCase


class RevisitSeedTest(MiningTestCase):

    def setUp(self):
        class SampleSeed0(seed.Seeder):
            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/foo/json'

        class SampleSeed1(seed.Seeder):
            revisit_after = 1  # hours

            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/foo/json'

        self.SampleSeed0 = SampleSeed0()
        self.SampleSeed1 = SampleSeed1()

    def test_insert_seed_uris_revisit_before_10_days_custom_revisit_after(self):
        # we consume generators to insert seed URI
        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed1]))

        seeded = ResourceURI.objects.all()
        self.assertEqual(1, len(seeded))

        s = seeded[0]
        s.last_visit_date = timezone.now() - timedelta(minutes=10)
        s.save()

        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed1]))
        seeded = ResourceURI.objects.all()
        self.assertEqual(1, len(seeded))

    def test_insert_seed_uris_revisit_after_10_days_custom_revisit_after(self):
        # we consume generators to insert seed URI
        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed1]))

        seeded = ResourceURI.objects.all()
        self.assertEqual(1, len(seeded))

        s = seeded[0]
        s.last_visit_date = timezone.now() - timedelta(days=10)
        s.save()

        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed1]))
        seeded = ResourceURI.objects.all()
        self.assertEqual(2, len(seeded))

    def test_insert_seed_uris_revisit_before_10_days_default_revisit_after(self):
        # we consume generators to insert seed URI
        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed0]))

        seeded = ResourceURI.objects.all()
        self.assertEqual(1, len(seeded))

        s = seeded[0]
        s.last_visit_date = timezone.now() - timedelta(days=9)
        s.save()

        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed0]))
        seeded = ResourceURI.objects.all()
        self.assertEqual(1, len(seeded))

    def test_insert_seed_uris_revisit_after_10_days_default_revisit_after(self):
        # we consume generators to insert seed URI
        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed0]))

        seeded = ResourceURI.objects.all()
        self.assertEqual(1, len(seeded))

        s = seeded[0]
        s.last_visit_date = timezone.now() - timedelta(days=10)
        s.save()

        list(insert_seed_uris(pattern='.*python.org/pypi/.*', seeders=[self.SampleSeed0]))
        seeded = ResourceURI.objects.all()
        self.assertEqual(2, len(seeded))


class SeedTest(MiningTestCase):
    test_data_dir = os.path.join(os.path.dirname(__file__), 'testfiles')

    def setUp(self):

        class SampleSeed0(seed.Seeder):
            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/thatbar/json'
                yield 'https://pypi.python.org/pypi/that/json'
                yield 'https://elsewehre.com'

        class SampleSeed1(seed.Seeder):
            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/igloo/json'
                yield 'https://pypi.python.org/pypi/someigloo/json'

        class SampleSeed2(seed.Seeder):
            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/igloo2/json'
                yield 'https://pypi.python.org/pypi/otherigloo/json'

        class SampleSeed3(seed.Seeder):
            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/foo/json'
                yield 'https://pypi.python.org/pypi/foobar/json'

        class SampleSeed4(seed.Seeder):
            def get_seeds(self):
                yield 'https://pypi.python.org/pypi/foo/json'
                yield 'https://pypi.python.org/pypi/foobaz/json'

        self.SampleSeed0 = SampleSeed0()
        self.SampleSeed1 = SampleSeed1()
        self.SampleSeed2 = SampleSeed2()
        self.SampleSeed3 = SampleSeed3()
        self.SampleSeed4 = SampleSeed4()

    @patch('discovery.seed.get_active_seeders')
    def test_seed_command(self, mock_get_active_seeders):
        output = StringIO()
        mock_get_active_seeders.return_value = [self.SampleSeed0]
        before = list(ResourceURI.objects.all().values_list('id'))

        management.call_command('seed', pattern=None, stdout=output)
        expected = 'Inserted 3 seed URIs\n'
        self.assertEqual(expected, output.getvalue())

        if before:
            seeded = ResourceURI.objects.exclude(uri__in=before)
        else:
            seeded = ResourceURI.objects.all()

        expected = sorted([
            'https://pypi.python.org/pypi/thatbar/json',
            'https://pypi.python.org/pypi/that/json',
            'https://elsewehre.com',
        ])
        self.assertEqual(expected, sorted([s.uri for s in seeded]))
        self.assertTrue(not all(s.is_visitable for s in seeded))
        self.assertEqual(3, len([s.is_visitable for s in seeded]))
        self.assertTrue(all(s.priority == SEED_PRIORITY for s in seeded))

    @patch('discovery.seed.get_active_seeders')
    def test_insert_seed_uris_inserts_uris_for_active_seeders_with_pattern(self, mock_get_active_seeders):
        mock_get_active_seeders.return_value = [self.SampleSeed1]
        before = list(ResourceURI.objects.all().values_list('id'))
        seeders = seed.get_active_seeders()
        results = sorted(insert_seed_uris(pattern='.*python.*igloo.json', seeders=seeders))
        if before:
            seeded = ResourceURI.objects.exclude(uri__in=before)
        else:
            seeded = ResourceURI.objects.all()

        expected = sorted([
            'https://pypi.python.org/pypi/igloo/json',
            'https://pypi.python.org/pypi/someigloo/json',
        ])

        self.assertEqual(expected, sorted(results))
        self.assertEqual(expected, sorted([s.uri for s in seeded]))
        self.assertTrue(all(s.is_visitable for s in seeded))
        self.assertTrue(all(s.priority == SEED_PRIORITY for s in seeded))

    def test_insert_seed_uris_inserts_uris_for_active_seeders_without_pattern(self):
        before = list(ResourceURI.objects.all().values_list('id'))

        results = list(insert_seed_uris(seeders=[self.SampleSeed1]))

        if before:
            seeded = ResourceURI.objects.exclude(uri__in=before)
        else:
            seeded = ResourceURI.objects.all()

        expected = sorted([
            'https://pypi.python.org/pypi/igloo/json',
            'https://pypi.python.org/pypi/someigloo/json',
        ])

        self.assertEqual(expected, sorted(results))
        self.assertEqual(expected, sorted([s.uri for s in seeded]))
        self.assertTrue(all(s.is_visitable for s in seeded))
        self.assertTrue(all(s.priority == SEED_PRIORITY for s in seeded))

    def test_insert_seed_uris_does_not_insert_duplicate(self):
        seeders = [self.SampleSeed3, self.SampleSeed4]
        before = list(ResourceURI.objects.all().values_list('id'))
        # seed twice
        seed_results = sorted(insert_seed_uris(seeders=seeders))
        no_seed_results = sorted(insert_seed_uris())

        if before:
            seeded = ResourceURI.objects.exclude(uri__in=before)
        else:
            seeded = ResourceURI.objects.all()

        expected = sorted([
            'https://pypi.python.org/pypi/foo/json',
            'https://pypi.python.org/pypi/foobar/json',
            'https://pypi.python.org/pypi/foobaz/json',
        ])

        self.assertEqual(expected, sorted(seed_results))
        self.assertEqual([], no_seed_results)
        self.assertEqual(expected, sorted([s.uri for s in seeded]))
        self.assertTrue(all(s.is_visitable for s in seeded))
        self.assertTrue(all(s.priority == SEED_PRIORITY for s in seeded))

    def test_get_active_seeders(self):
        # note: this is to avoid that activate seeds by mistake
        # and needs to be updated each time we enable a new seed
        seeds = [c.__class__.__name__ for c in seed.get_active_seeders()]
        expected = [
            'NpmSeed',
        ]
        assert sorted(expected) == sorted(seeds)

    def test_get_configured_seeders(self):
        seeders = seed.get_configured_seeders()
        expected = [
            'discovery.visitors.npm.NpmSeed',
        ]
        assert sorted(expected) == sorted(seeders)
