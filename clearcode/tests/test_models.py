#
# Copyright (c) 2020 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#
import datetime

from django.test import TestCase
from django.utils import timezone

from clearcode.models import CDitem


class CDitemManagerModifiedAfterTestCase(TestCase):
    def setUp(self):
        self.cditem0 = CDitem.objects.create(path="npm/name/version")

    def test_modified_after_1_day_old(self):
        test_date = datetime.datetime.now() - datetime.timedelta(days=1)
        self.assertIsNotNone(CDitem.objects.modified_after(test_date))
        self.assertEqual(1, len(CDitem.objects.modified_after(test_date)))

    def test_modified_after_1_week_old(self):
        test_date = datetime.datetime.now() - datetime.timedelta(days=7)
        self.assertIsNotNone(CDitem.objects.modified_after(test_date))
        self.assertEqual(1, len(CDitem.objects.modified_after(test_date)))

    def test_modified_after_1_day_new(self):
        test_date = datetime.datetime.now() + datetime.timedelta(days=1)
        self.assertIsNotNone(CDitem.objects.modified_after(test_date))
        self.assertEqual(0, len(CDitem.objects.modified_after(test_date)))

    def test_modified_after_1_week_new(self):
        test_date = datetime.datetime.now() + datetime.timedelta(days=7)
        self.assertIsNotNone(CDitem.objects.modified_after(test_date))
        self.assertEqual(0, len(CDitem.objects.modified_after(test_date)))


class CDitemManagerTestCase(TestCase):
    def test_known_package_types(self):
        # This path starts with npm, which is known
        cditem_1 = CDitem.objects.create(path="npm/name/version")
        # asdf is not a proper type
        CDitem.objects.create(path="asdf/name/version")
        cditems = list(CDitem.objects.known_package_types())
        self.assertEqual(1, len(cditems))
        cditem = cditems[0]
        self.assertEqual(cditem_1, cditem)

    def test_definitions(self):
        expected_definition = CDitem.objects.create(
            path="composer/packagist/yoast/wordpress-seo/revision/9.5-RC3.json"
        )
        # harvest should not be in cditems
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6/tool/scancode/3.2.2.json"
        )
        cditems = list(CDitem.objects.definitions())
        self.assertEqual(1, len(cditems))
        definition = cditems[0]
        self.assertEqual(expected_definition, definition)

    def test_scancode_harvests(self):
        expected_harvest = CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6/tool/scancode/3.2.2.json"
        )
        # unexpected_harvest should not be in cditems
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6/tool/licensee/9.13.0.json"
        )
        harvests = list(CDitem.objects.scancode_harvests())
        self.assertEqual(1, len(harvests))
        harvest = harvests[0]
        self.assertEqual(expected_harvest, harvest)

    def test_mappable(self):
        definition_1 = CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6.json"
        )
        # This should not be mappable
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.quarkus/quarkus-jsonb/revision/0.26.1.json",
            last_map_date=timezone.now(),
            map_error="error",
        )
        harvest = CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6/tool/scancode/3.2.2.json"
        )
        mappables = list(CDitem.objects.mappable())
        self.assertEqual(2, len(mappables))
        self.assertIn(definition_1, mappables)
        self.assertIn(harvest, mappables)

    def test_mappable_definitions(self):
        definition_1 = CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6.json"
        )
        # This should not be mappable
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.quarkus/quarkus-jsonb/revision/0.26.1.json",
            last_map_date=timezone.now(),
            map_error="error",
        )
        # This should not be mappable
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6/tool/scancode/3.2.2.json"
        )
        mappables = list(CDitem.objects.mappable_definitions())
        self.assertEqual(1, len(mappables))
        definition = mappables[0]
        self.assertEqual(definition_1, definition)

    def test_mappable_scancode_harvests(self):
        harvest_1 = CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6/tool/scancode/3.2.2.json"
        )
        # This should not be mappable
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.cucumber/cucumber-core/revision/5.0.0-RC1/tool/scancode/3.2.2.json",
            last_map_date=timezone.now(),
            map_error="error",
        )
        # This should not be mappable
        CDitem.objects.create(
            path="sourcearchive/mavencentral/io.nats/jnats/revision/2.6.6.json"
        )
        mappables = list(CDitem.objects.mappable_scancode_harvests())
        self.assertEqual(1, len(mappables))
        harvest = mappables[0]
        self.assertEqual(harvest_1, harvest)
