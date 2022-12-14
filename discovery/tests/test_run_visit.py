#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from operator import itemgetter
from io import StringIO

from collections import Counter
from django.core import management
from django.forms.models import model_to_dict

from discovery.utils_test import MiningTestCase
from discovery.management.commands.run_visit import visit_uri
from discovery.models import ResourceURI
from discovery.route import Router
from discovery.visitors import URI


class RunVisitWithCounterTest(MiningTestCase):

    def test_visit_uri_with_counter_0_max_uris_3_multi_uri(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-0-max-uris-3-multi-uri1.com', package_url='pkg:npm/foobar@12.3.1'),
                    URI(uri='http://test-counter-0-max-uris-3-multi-uri2.com', package_url='pkg:npm/foobar@12.3.2'),
                    URI(uri='http://test-counter-0-max-uris-3-multi-uri3.com', package_url='pkg:npm/foobar@12.3.3'),
                    URI(uri='http://test-counter-0-max-uris-3-multi-uri4.com', package_url='pkg:npm/foobar@12.3.4'),
                    URI(uri='http://test-counter-0-max-uris-3-multi-uri5.com', package_url='pkg:npm/foobar@12.3.5'),
                    URI(uri='http://test-counter-0-max-uris-3-multi-uri6.com', package_url='pkg:npm/foobar@12.3.5')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 0

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=3, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-3-multi-uri1.com')
        self.assertEqual(1, visited.count())
        self.assertEqual('pkg:npm/foobar@12.3.1', visited[0].package_url)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-3-multi-uri2.com')
        self.assertEqual(1, visited.count())
        self.assertEqual('pkg:npm/foobar@12.3.2', visited[0].package_url)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-3-multi-uri3.com')
        self.assertEqual(1, visited.count())
        self.assertEqual('pkg:npm/foobar@12.3.3', visited[0].package_url)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-3-multi-uri4.com')
        self.assertEqual(1, visited.count())
        self.assertEqual('pkg:npm/foobar@12.3.4', visited[0].package_url)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-3-multi-uri5.com')
        self.assertEqual(0, visited.count())

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-3-multi-uri6.com')
        self.assertEqual(0, visited.count())

    def test_visit_uri_with_counter_0_max_uris_1_multi_uri(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-0-max-uris-1-multi-uri1.com'),
                    URI(uri='http://test-counter-0-max-uris-1-multi-uri2.com'),
                    URI(uri='http://test-counter-0-max-uris-1-multi-uri3.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 0

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=1, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-1-multi-uri1.com')
        self.assertEqual(1, visited.count())

        # MAX_URIS=1 still gives us two URIs
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-1-multi-uri2.com')
        self.assertEqual(1, visited.count())

        # ... but not 3
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-0-max-uris-1-multi-uri3.com')
        self.assertEqual(0, visited.count())

    def test_visit_uri_with_counter_10_max_uris_10_multi_uri(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-10-max-uris-10-multi-uri1.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri2.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri3.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri4.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri5.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri6.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri7.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri8.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri9.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri10.com'),
                    URI(uri='http://test-counter-10-max-uris-10-multi-uri11.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 1

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=1, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri1.com')
        self.assertEqual(1, visited.count())

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri2.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri3.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri4.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri5.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri6.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri7.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri8.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri9.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri10.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10-multi-uri11.com')
        self.assertEqual(0, visited.count())

    def test_visit_uri_with_counter_3_max_uris_3_multi_uri(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-3-max-uris-3-multi-uri1.com'),
                    URI(uri='http://test-counter-3-max-uris-3-multi-uri2.com'),
                    URI(uri='http://test-counter-3-max-uris-3-multi-uri3.com'),
                    URI(uri='http://test-counter-3-max-uris-3-multi-uri4.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 1

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=1, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-3-max-uris-3-multi-uri1.com')
        self.assertEqual(1, visited.count())

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-3-max-uris-3-multi-uri2.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-3-max-uris-3-multi-uri3.com')
        self.assertEqual(0, visited.count())
        visited = ResourceURI.objects.filter(
            uri='http://test-counter-3-max-uris-3-multi-uri3.com')
        self.assertEqual(0, visited.count())

    def test_visit_uri_with_counter_1_max_uris_1_multi_uri(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-1-max-uris-1-multi-uri1.com'),
                    URI(uri='http://test-counter-1-max-uris-1-multi-uri2.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 1

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=1, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-1-max-uris-1-multi-uri1.com')
        self.assertEqual(1, visited.count())

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-1-max-uris-1-multi-uri2.com')
        self.assertEqual(0, visited.count())

    def test_visit_uri_with_counter_10_max_uris_10(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-10-max-uris-10.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 10

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=10, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-10-max-uris-10.com')
        self.assertEqual(1, visited.count())

    def test_visit_uri_with_counter_3_max_uris_3(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-3-max-uris-3.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 3

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=3, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-3-max-uris-3.com')
        self.assertEqual(1, visited.count())

    def test_visit_uri_with_counter_1_max_uris_1(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-1-max-uris-1.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 1

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=1, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-1-max-uris-1.com')
        self.assertEqual(1, visited.count())

    def test_visit_uri_with_counter_2_max_uris_1(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-2-max-uris-1.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 2

        visit_uri(resource_uri, _visit_router=router,
                  max_uris=1, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-2-max-uris-1.com')
        self.assertEqual(0, visited.count())

    def test_visit_uri_with_counter_1_no_max_uri(self):
        # setup
        # build a test visitor and register it in a router
        uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test-counter-2-max-uris-1.com')], None, None

        router = Router()
        router.append(uri, mock_visitor)

        # seed ResourceURI with a uri
        resource_uri = ResourceURI.objects.insert(uri=uri)
        resource_uri.is_visitable = True
        resource_uri.save()

        counter = Counter()

        # test proper
        visitor = router.resolve(resource_uri.uri)
        key = visitor.__module__ + visitor.__name__
        counter[key] += 1

        visit_uri(
            resource_uri, _visit_router=router, uri_counter_by_visitor=counter)

        visited = ResourceURI.objects.filter(
            uri='http://test-counter-2-max-uris-1.com')
        self.assertEqual(1, visited.count())


class RunVisitTest(MiningTestCase):

    def setUp(self):
        self.uri = 'http://nexb_visit.com'

        def mock_visitor(uri):
            return [URI(uri='http://test.com')], None, None

        def mock_visitor2(uri):
            return [
                URI(uri='http://test.com', package_url='pkg:npm/foobar@12.3.1'),
                URI(uri='http://test.com', visited=True,
                    data={'some': 'data'}),
            ], None, None

        self.router = Router()
        self.router.append(self.uri, mock_visitor)

        self.router2 = Router()
        self.router2.append(self.uri, mock_visitor2)

        self.resource_uri = ResourceURI.objects.insert(uri=self.uri)
        self.resource_uri.is_visitable = True
        self.resource_uri.save()

    def tearDown(self):
        ResourceURI.objects.all().delete()

    def test_visit_uri(self):
        visit_uri(self.resource_uri, _visit_router=self.router)
        visited = ResourceURI.objects.filter(uri='http://test.com')
        self.assertEqual(1, visited.count())

    def test_visit_uri_with_no_route_defined_does_not_visit(self):
        resource_uri = ResourceURI.objects.create(uri='http://undefined-route.com')
        resource_uri.is_visitable = True
        resource_uri.save()

        visit_uri(resource_uri, _visit_router=self.router)
        try:
            ResourceURI.objects.get(uri='http://test.com')
            self.fail('URI should not have been created.')
        except ResourceURI.DoesNotExist:
            pass

    def test_run_visit_command(self):
        output = StringIO()
        management.call_command('run_visit', exit_on_empty=True, stdout=output)
        expected = 'Visited 0 URIs\nInserted 0 new URIs\n'
        self.assertEquals(expected, output.getvalue())

    def test_visit_uri_always_inserts_new_uri(self):
        # test proper
        visit_uri(self.resource_uri, _visit_router=self.router2)
        visited = ResourceURI.objects.filter(uri='http://test.com').order_by('-package_url')
        expected = [
            URI(uri=u'http://test.com', data=u"{'some': 'data'}"),
            URI(uri=u'http://test.com', package_url='pkg:npm/foobar@12.3.1'),
        ]

        results = sorted(URI.from_db(ruri) for ruri in visited)
        self.assertEqual(expected, results)

    def test_visit_uri_always_inserts_new_uri_unless_there_is_pending_for_visit(self):
        # create a uri that is already pending visit
        resource_uri2 = ResourceURI.objects.insert(uri='http://test.com')
        resource_uri2.is_visitable = True
        resource_uri2.save()

        # test proper
        visit_uri(self.resource_uri, _visit_router=self.router)
        visited = ResourceURI.objects.filter(uri='http://test.com')
        expected = [
            resource_uri2
        ]

        self.assertEqual(expected, list(visited))
