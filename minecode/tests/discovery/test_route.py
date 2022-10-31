#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from django.test import TestCase

from discovery import route
from discovery.route import Rule


class RouteTest(TestCase):

    def test_rule(self):
        self.assertRaises(AssertionError, Rule, '', '')

        class non_callable(object):
            pass

        self.assertRaises(AssertionError, Rule, 'abc', non_callable)

        class RoutableClass(object):
            """ A callable class can be routed."""

            def __call__(self):
                pass

        ca = RoutableClass()
        Rule('asas', ca)
        Rule('asas', RoutableClass)

        def func():
            pass

        Rule('asas', func)

        import re
        invalid_regex = '(({wewew'
        self.assertRaises(re.error, Rule, invalid_regex, func)

    def test_class_routing(self):
        uris = route.Router()

        @uris.route('this')
        class CallableClass(object):
            """ A callable class can be routed."""

            def __call__(self, uri, *args, **kwargs):
                return uri

        self.assertEqual('this', uris.process('this'))

    def test_that_each_processing_of_routed_class_is_done_with_a_new_instance_that_does_not_share_state(self):
        import time
        uris = route.Router()

        @uris.route('this', 'that')
        class CallableClass(object):
            """ A callable class can be routed."""

            def __init__(self):
                # some more or less unique thing for a given instance
                time.sleep(0.1)
                self.ts = time.time()

            def __call__(self, uri):
                return self.ts

        # ensure that two routes with the same object are same class
        thi = uris.resolve('this')
        thi2 = uris.resolve('this')
        self.assertTrue(thi is thi2)
        tha = uris.resolve('that')
        self.assertTrue(thi is tha)

        # ensure that processing of routes for the same registered class
        # is done by different objects with different state
        p1 = uris.process('this')
        p2 = uris.process('this')
        self.assertNotEqual(p1, p2)
        p3 = uris.process('this')
        p4 = uris.process('that')
        self.assertNotEqual(p3, p4)

    def test_that_subclasses_are_routed_correctly_with_append_to_route(self):

        class CallableParentClass(object):

            def __call__(self, uri):
                return self.myfunc()

            def myfunc(self):
                pass

        class CallableSubClass1(CallableParentClass):

            def myfunc(self):
                return 'done1'

        class CallableSubClass2(CallableParentClass):

            def myfunc(self):
                return 'done2'

        uris = route.Router()
        uris.append('base', CallableParentClass)
        uris.append('this', CallableSubClass1)
        uris.append('that', CallableSubClass2)

        self.assertEqual(None, uris.process('base'))
        self.assertEqual('done1', uris.process('this'))
        self.assertEqual('done2', uris.process('that'))

    def test_that_subclasses_are_routed_correctly_with_class_decorator(self):
        uris = route.Router()

        class CallableParentClass(object):
            """
            Note: The parent class CANNOT be decorated. Only subclasses can
            """

            def __call__(self, uri):
                return self.myfunc()

            def myfunc(self):
                raise NotImplementedError

        @uris.route('this')
        class CallableSubClass1(CallableParentClass):

            def myfunc(self):
                return 'done1'

        @uris.route('that')
        class CallableSubClass2(CallableParentClass):

            def __call__(self, uri):
                return 'done3'

        self.assertEqual('done1', uris.process('this'))
        self.assertEqual('done3', uris.process('that'))

    def test_rule_match(self):

        def func(uri):
            pass

        r = Rule('asas', func)
        self.assertTrue(r.match('asas'))
        self.assertFalse(r.match('bbb'))

        r = Rule('.*abc', func)
        self.assertTrue(r.match('abc'))
        self.assertTrue(r.match('123abc'))
        self.assertFalse(r.match('bbb'))
        self.assertFalse(r.match('abcXYZ'))

        r = Rule('https*://', func)
        self.assertTrue(r.match('http://'))
        self.assertTrue(r.match('https://'))

    def test_routing_resolving_and_exceptions(self):
        uris = route.Router()

        @uris.route(r'http://nexb\.com')
        def myroute(uri):
            pass

        @uris.route(r'http://nexb\.com.*')
        def myroute2(uri):
            pass

        self.assertRaises(route.RouteAlreadyDefined, uris.append,
                          r'http://nexb\.com', myroute)
        self.assertRaises(route.RouteAlreadyDefined, uris.append,
                          r'http://nexb\.com', myroute)

        self.assertRaises(route.MultipleRoutesDefined, uris.resolve,
                          r'http://nexb.com')
        self.assertRaises(route.NoRouteAvailable, uris.resolve, 'impossible')

    def test_route_resolution_and_execution(self):
        uris = route.Router()

        @uris.route(r'http://nexb\.com')
        def myroute(uri):
            return 'r1'

        u1 = 'http://nexb.com'
        self.assertEqual('r1', myroute(u1))

        @uris.route(r'http://dejacode\.com')
        def myroute2(uri):
            return 'r2'

        u1 = 'http://nexb.com'
        self.assertEqual(myroute.__name__, uris.resolve(u1).__name__)

        # these three calls are equivalent: the uri determines what is executed
        self.assertEqual('r1', myroute(u1))
        self.assertEqual('r1', myroute2(u1))
        self.assertEqual('r1', uris.process(u1))

        u2 = 'http://dejacode.com'
        self.assertEqual(myroute2.__name__, uris.resolve(u2).__name__)

        # these three calls are equivalent: the uri determines what is executed
        self.assertEqual('r2', myroute2(u2))
        self.assertEqual('r2', myroute(u2))
        self.assertEqual('r2', uris.process(u2))

    def test_that_multiple_patterns_can_be_used_in_a_route_decorator(self):
        uris = route.Router()

        @uris.route(r'http://nexb\.com',
                    r'http://deja\.com')
        def myroute(uri):
            return 'r1'

        u1 = 'http://nexb.com'
        self.assertEqual('r1', myroute(u1))
        u1 = 'http://deja.com'
        self.assertEqual('r1', myroute(u1))

    def test_translate_globs_can_be_used_instead_of_regex_patterns(self):
        uris = route.Router()

        from fnmatch import translate

        @uris.route(translate('http://nexb.com/'))
        def myroute(uri):
            return 'r1'

        u1 = 'http://nexb.com/'
        self.assertEqual('r1', myroute(u1))

        @uris.route(translate('http://nexb.com/*/*/'))
        def myroute2(uri):
            return 'r2'

        u1 = 'http://nexb.com/somepath/otherpath/'
        self.assertEqual('r2', myroute(u1))
        u1 = 'http://nexb.com/somepath/yetanotherotherpath/'
        self.assertEqual('r2', myroute(u1))

    def test_is_routable(self):
        uris = route.Router()

        @uris.route(r'http://nexb\.com',
                    r'http://deja\.com')
        def myroute(uri):
            pass

        @uris.route(r'http://nexc\.com',
                    r'http://dejb\.com')
        def myroute2(uri):
            pass

        self.assertTrue(uris.is_routable('http://nexb.com'))
        self.assertTrue(uris.is_routable('http://deja.com'))
        self.assertTrue(uris.is_routable('http://nexc.com'))
        self.assertTrue(uris.is_routable('http://dejb.com'))
        self.assertFalse(uris.is_routable('https://deja.com'))
