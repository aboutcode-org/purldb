#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from discovery import visitors
from discovery import mappers

from discovery.models import ResourceURI
from packagedb.models import Package
from discovery.models import get_canonical
from discovery.models import ScannableURI


class ResourceURIModelTestCase(TestCase):

    def setUp(self):
        self.res = ResourceURI.objects.insert(
            uri='http://repo1.maven.org/maven2/org/ye/mav/mav-all/1.0/mav-all-1.0.pom')

    def test_get_canonical(self):
        data = (
            ('http://www.nexb.com', 'http://www.nexb.com/'),
            ('http://www.nexb.com/', 'http://www.nexb.com/'),
            ('http://www.nexb.com/a/b/../../c/', 'http://www.nexb.com/c/'),
            ('http://www.nexb.com:80', 'http://www.nexb.com/'),
            ('https://www.nexb.com:443', 'https://www.nexb.com/'),
            ('http://www.nexb.com:443', 'http://www.nexb.com:443/'),
            ('https://www.nexb.com:80', 'https://www.nexb.com:80/'),
            ('http://www.nexb.com/A 0.0.1 Alpha/a_0_0_1.zip',
             'http://www.nexb.com/A%200.0.1%20Alpha/a_0_0_1.zip'),
        )
        for test, expected in data:
            self.assertEqual(expected, get_canonical(test))

    def test_is_routable_flags_are_not_overwritten_on_save(self):
        self.assertTrue(self.res.is_visitable)
        self.assertTrue(self.res.is_mappable)
        self.res.sha1 = 'a' * 40
        self.res.save()
        res1 = ResourceURI.objects.get(
            uri='http://repo1.maven.org/maven2/org/ye/mav/mav-all/1.0/mav-all-1.0.pom')
        self.assertTrue(res1.is_visitable)
        self.assertTrue(res1.is_mappable)
        res1.save()
        res2 = ResourceURI.objects.get(
            uri='http://repo1.maven.org/maven2/org/ye/mav/mav-all/1.0/mav-all-1.0.pom')
        self.assertTrue(res2.is_visitable)
        self.assertTrue(res2.is_mappable)


class ResourceURIManagerTestCase(TestCase):

    def setUp(self):
        self.uri = 'https://sourceforge.net/sitemap.xml'
        self.resource = ResourceURI.objects.insert(uri=self.uri, priority=100)

    def test_insert(self):
        self.assertEqual(get_canonical(self.uri), self.resource.canonical)
        self.assertEqual(100, self.resource.priority)
        # None when same canonical URI already exists.
        self.assertIsNone(ResourceURI.objects.insert(self.uri))

    def test_never_visited(self):
        self.assertIsNone(self.resource.last_visit_date)
        self.assertIsNone(self.resource.wip_date)
        self.assertTrue(ResourceURI.objects.never_visited())

        self.resource.last_visit_date = timezone.now()
        self.resource.save()
        self.assertFalse(ResourceURI.objects.never_visited())

    def test_in_progress(self):
        self.assertFalse(ResourceURI.objects.in_progress())
        self.resource.wip_date = timezone.now()
        self.resource.save()
        self.assertTrue(ResourceURI.objects.in_progress())

    def test_completed(self):
        self.assertFalse(ResourceURI.objects.visited())
        self.resource.last_visit_date = timezone.now()
        self.resource.save()
        self.assertTrue(ResourceURI.objects.visited())

    def test_successful(self):
        self.assertFalse(ResourceURI.objects.successfully_visited())
        self.resource.last_visit_date = timezone.now()
        self.resource.save()
        self.assertTrue(ResourceURI.objects.successfully_visited())
        self.resource.visit_error = 'error'
        self.resource.save()
        self.assertFalse(ResourceURI.objects.successfully_visited())

    def test_unsuccessful(self):
        self.assertFalse(ResourceURI.objects.unsuccessfully_visited())
        self.resource.last_visit_date = timezone.now()
        self.resource.save()
        self.assertFalse(ResourceURI.objects.unsuccessfully_visited())
        self.resource.visit_error = 'error'
        self.resource.save()
        self.assertTrue(ResourceURI.objects.unsuccessfully_visited())

    def test_needs_revisit_force_revisit_at_0_hours(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.save()

        self.assertTrue(ResourceURI.objects.needs_revisit(uri=self.uri, hours=0))

    def test_needs_revisit_very_old_visit(self):
        self.resource.last_visit_date = timezone.now() - timedelta(days=20)
        self.resource.save()

        self.assertTrue(ResourceURI.objects.needs_revisit(uri=self.uri, hours=240))

    def test_needs_revisit_near_visit(self):
        self.resource.last_visit_date = timezone.now() - timedelta(hours=3)
        self.resource.save()

        self.assertTrue(ResourceURI.objects.needs_revisit(uri=self.uri, hours=2))

    def test_needs_revisit_recent_visit(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.save()

        self.assertFalse(ResourceURI.objects.needs_revisit(uri=self.uri, hours=2))

    def test_needs_revisit_never_been_visited(self):
        self.assertFalse(ResourceURI.objects.needs_revisit(uri=self.uri, hours=200))


class ResourceURIManagerGetRevisitablesUnmappableURITestCase(TestCase):

    def setUp(self):
        self.uri = 'https://sourceforge.net/sitemap.xml'
        self.resource = ResourceURI.objects.insert(uri=self.uri, priority=100)

    def test_get_revisitables_last_visit_date_now(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.save()

        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=0).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=1).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=240).count())

    def test_get_revisitables_last_visit_date_10_days_ago(self):
        self.resource.last_visit_date = timezone.now() - timedelta(hours=240)
        self.resource.save()

        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=0).count())
        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=1).count())
        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=240).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=241).count())


class ResourceURIManagerGetRevisitablesMappableURITestCase(TestCase):

    def setUp(self):
        # this is a mappable ResourceURI
        self.uri = 'http://repo1.maven.org/maven2/org/ye/mav/mav-all/1.0/mav-all-1.0.pom'
        self.resource = ResourceURI.objects.insert(uri=self.uri, priority=100)

    def test_get_revisitables_unmapped_last_visit_date_now(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.save()

        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=0).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=1).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=240).count())

    def test_get_revisitables_unmapped_last_visit_date_less_than_threshold(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.save()

        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=1).count())

    def test_get_revisitables_unmapped_last_visit_date_10_days_ago(self):
        self.resource.last_visit_date = timezone.now() - timedelta(hours=240)
        self.resource.save()

        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=0).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=1).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=240).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=241).count())

    def test_get_revisitables_mapped_last_visit_date_now(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.last_map_date = timezone.now()
        self.resource.save()

        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=0).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=1).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=240).count())

    def test_get_revisitables_mapped_last_visit_date_less_than_threshold(self):
        self.resource.last_visit_date = timezone.now()
        self.resource.last_map_date = timezone.now()
        self.resource.save()

        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=1).count())

    def test_get_revisitables_mapped_last_visit_date_10_days_ago(self):
        self.resource.last_visit_date = timezone.now() - timedelta(hours=240)
        self.resource.last_map_date = timezone.now()
        self.resource.save()

        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=0).count())
        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=1).count())
        self.assertEqual(1, ResourceURI.objects.get_revisitables(hours=240).count())
        self.assertEqual(0, ResourceURI.objects.get_revisitables(hours=241).count())


class ResourceURIManagerGetNextVisitableUnmappableURITestCase(TestCase):

    def setUp(self):
        self.uri0 = 'https://sourceforge.net/sitemap.xml'
        self.uri1 = 'https://sourceforge.net/sitemap-0.xml'
        self.resource0 = ResourceURI.objects.insert(uri=self.uri0, priority=1)
        self.resource1 = ResourceURI.objects.insert(uri=self.uri1, priority=2)

    def test_get_next_visitable_unvisited(self):
        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_none_when_both_visited_less_than_10_days_ago(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=24)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=24)
        self.resource0.save()
        self.resource1.save()

        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_when_both_visited_10_days_ago(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=240)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=240)
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_when_one_unvisited_and_one_visited_less_than_10_days_ago(self):
        self.resource0.last_visit_date = None
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=24)
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

        self.resource0.last_visit_date = timezone.now() - timedelta(hours=24)
        self.resource1.last_visit_date = None
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_when_one_visited_more_and_one_visited_less_than_10_days_ago(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=24)
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

        self.resource0.last_visit_date = timezone.now() - timedelta(hours=24)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())


class ResourceURIManagerGetNextVisitableMappableURITestCase(TestCase):

    def setUp(self):
        # this is a mappable ResourceURI
        self.uri0 = 'http://repo1.maven.org/maven2/org/ye/mav/mav-all/1.0/mav-all-1.0.pom'
        self.uri1 = 'http://repo1.maven.org/maven2/org/ye/mav/mav-all/1.1/mav-all-1.1.pom'
        self.resource0 = ResourceURI.objects.insert(uri=self.uri0, priority=100)
        self.resource1 = ResourceURI.objects.insert(uri=self.uri1, priority=100)

    def test_get_next_visitable_unvisited(self):
        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_visited_unmapped(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource0.save()
        self.resource1.save()

        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_visited_10_days_ago_mapped(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource0.last_map_date = timezone.now()
        self.resource1.last_map_date = timezone.now()
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_visited_10_days_ago_one_unmapped(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=250)
        self.resource0.last_map_date = timezone.now()
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource0, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

        self.resource0.last_map_date = None
        self.resource1.last_map_date = timezone.now()
        self.resource0.save()
        self.resource1.save()

        self.assertEqual(self.resource1, ResourceURI.objects.get_next_visitable())
        self.assertIsNone(ResourceURI.objects.get_next_visitable())

    def test_get_next_visitable_recently_visited_mapped(self):
        self.resource0.last_visit_date = timezone.now() - timedelta(hours=2)
        self.resource1.last_visit_date = timezone.now() - timedelta(hours=2)
        self.resource0.last_map_date = timezone.now()
        self.resource1.last_map_date = timezone.now()
        self.resource0.save()
        self.resource1.save()

        self.assertIsNone(ResourceURI.objects.get_next_visitable())


class ResourceURIManagerGetMappablesTestCase(TestCase):

    def setUp(self):
        self.uri1 = 'maven-index://repo1.maven.org/o/a/this.jar'
        self.uri2 = 'maven-index://repo1.maven.org/o/a/thisother.jar'
        self.resource1 = ResourceURI.objects.create(uri=self.uri1, priority=1, last_visit_date=timezone.now())
        self.resource2 = ResourceURI.objects.create(uri=self.uri2, priority=2, last_visit_date=timezone.now())

    def test_get_mappables(self):
        assert self.resource1.is_mappable
        assert self.resource2.is_mappable
        self.assertEqual(2, ResourceURI.objects.get_mappables().count())
        self.resource1.last_map_date = timezone.now()
        self.resource1.save()
        resource1 = ResourceURI.objects.get(id=self.resource1.id)
        self.assertEqual([self.resource2], list(ResourceURI.objects.get_mappables()))

    def test_get_mappables__map_error_must_make_a_resourceuri_non_mappable(self):
        assert self.resource1.is_mappable
        self.assertEqual(2, ResourceURI.objects.get_mappables().count())
        self.resource1.map_error = 'Some error happened'
        self.resource2.map_error = 'Some error happened'
        self.resource1.save()
        self.resource2.save()
        resource1 = ResourceURI.objects.get(id=self.resource1.id)
        self.assertEqual([], list(ResourceURI.objects.get_mappables()))


class ScannableURIManagerTestCase(TestCase):
    def setUp(self):
        self.test_uri1 = 'http://example.com'
        self.test_package1 = Package.objects.create(download_url=self.test_uri1, name='Foo', version='12.34')
        self.scannable_uri1 = ScannableURI.objects.create(uri=self.test_uri1, package=self.test_package1,
                                                          scan_status=ScannableURI.SCAN_NEW)
        self.test_uri2 = 'http://elpmaxe.com'
        self.test_package2 = Package.objects.create(download_url=self.test_uri2, name='Bar', version='11.75')
        self.scannable_uri2 = ScannableURI.objects.create(uri=self.test_uri2, package=self.test_package2,
                                                          scan_status=ScannableURI.SCAN_SUBMITTED)
        self.test_uri3 = 'http://nexb.com'
        self.test_package3 = Package.objects.create(download_url=self.test_uri3, name='Baz', version='5')
        self.scannable_uri3 = ScannableURI.objects.create(uri=self.test_uri3, package=self.test_package3,
                                                          scan_status=ScannableURI.SCAN_IN_PROGRESS)
        self.test_uri4 = 'http://realsite.com'
        self.test_package4 = Package.objects.create(download_url=self.test_uri4, name='Qux', version='87')
        self.scannable_uri4 = ScannableURI.objects.create(uri=self.test_uri4, package=self.test_package4,
                                                          scan_status=ScannableURI.SCAN_COMPLETED)

    def test_ScannableURIManager_get_scannables(self):
        result = ScannableURI.objects.get_scannables()
        self.assertTrue(1, len(result))
        self.assertTrue(self.scannable_uri1, result[0])

    def test_ScannableURIManager_get_next_scannable(self):
        result = ScannableURI.objects.get_next_scannable()
        self.assertTrue(self.test_uri1, result.uri)
        self.assertTrue(result.wip_date)

    def test_ScannableURIManager_get_processables(self):
        result = ScannableURI.objects.get_processables()
        self.assertTrue(3, len(result))
        self.assertIn(self.scannable_uri2, result)
        self.assertIn(self.scannable_uri3, result)
        self.assertIn(self.scannable_uri4, result)

    def test_ScannableURI_get_next_processable(self):
        result = ScannableURI.objects.get_next_processable()
        # scannable_uri4 should always be returned in front of scannable_uri2 and scannable_uri3
        # because its status value is higher (SCAN_COMPLETED = 3, vs SCAN_SUBMITTED = 1 vs SCAN_IN_PROGRESS = 2)
        self.assertEqual(self.test_uri4, result.uri)
        self.assertTrue(result.wip_date)


class ScannableURIModelTestCase(TestCase):
    def setUp(self):
        self.test_uri = 'http://example.com'
        self.test_package = Package.objects.create(download_url=self.test_uri, name='Foo', version='12.34')

    def test_ScannableURI_create_basic_record(self):
        scannable_uri = ScannableURI.objects.create(uri=self.test_uri, package=self.test_package)
        result = ScannableURI.objects.get(uri=self.test_uri)
        self.assertEqual(self.test_uri, result.uri)
        self.assertEqual(self.test_package, result.package)

    def test_ScannableURI_save(self):
        test_error_message = 'error'
        scannable_uri = ScannableURI.objects.create(uri=self.test_uri, package=self.test_package)
        self.assertFalse(scannable_uri.scan_error)
        scannable_uri.scan_error = test_error_message
        scannable_uri.save()
        result = ScannableURI.objects.get(uri=self.test_uri)
        self.assertEqual(test_error_message, result.scan_error)

    def test_ScannableURI_save_set_canonical_uri(self):
        scannable_uri = ScannableURI(uri=self.test_uri, package=self.test_package)
        self.assertFalse(scannable_uri.canonical)
        scannable_uri.save()
        result = ScannableURI.objects.get(uri=self.test_uri)
        self.assertEqual('http://example.com/', result.canonical)
