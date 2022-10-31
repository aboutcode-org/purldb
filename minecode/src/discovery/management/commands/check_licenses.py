#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import codecs
from functools import reduce
import json
import logging
import operator
import os
import sys

from django.db.models import Q

from packagedb.models import Package

from discovery.management.commands import VerboseCommand

"""
Utility command to find license oddities.
"""
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


class Command(VerboseCommand):
    help = ('Find packages with an ambiguous declared license.')

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output', type=str,
            help='Define the output file name')

        parser.add_argument(
            '--types',
            dest='types',
            default='maven',
            action='store',
            help='Package types to check, comma-separated [maven]')

    def handle(self, *args, **options):
        """
        Find packages with an ambiguous declared license, typically  with a
        license_expression that contains licenses suchas  "unknown",
        "proprietary" and "commercial" licenses.
        """
        logger.setLevel(self.get_verbosity(**options))

        output_filename = options.get('output')

        types = options.get('types')
        types = [t.strip() for t in types.split(',') if t.strip()]

        packages_with_ambiguous_licenses = find_ambiguous_packages(types=types)

        file_location = os.path.abspath(output_filename)
        found_counter = dump(
            packages=packages_with_ambiguous_licenses, json_location=file_location)

        visited_counter = Package.objects.filter(type__in=types).count()

        self.stdout.write('Visited {} packages'.format(visited_counter))
        self.stdout.write('Found {} possible packages'.format(found_counter))
        if found_counter > 0:
            self.stdout.write('Found packages dumped to: {}'.format(file_location))


def find_ambiguous_packages(types=('maven',), keywords=('unknown', 'proprietary', 'commercial',)):
    """
    Search the package DB and yield the package that declared_license and license_expression
    contain "unknown", "proprietary" and "commercial" words.
    """
    # filter to detect declared_license field
    filter_expression = [Q(declared_license__icontains=word) for word in keywords]
    # filter to detect license_expression field, add or relationship between these two fields
    filter_expression.extend([Q(license_expression__icontains=word) for word in keywords])
    license_filter = reduce(operator.or_, filter_expression)

    for package in Package.objects.filter(type__in=types).filter(license_filter):
        yield package


def dump(packages, json_location):
    """
    Dump the packages as json format at the passing json_location and return the count of the packages.
    """
    if not packages:
        return 0
    packages = [p.to_dict() for p in packages]
    if packages:
        with codecs.open(json_location, mode='wb', encoding='utf-8') as expect:
            json.dump(packages, expect, indent=2, separators=(',', ': '))
    return len(packages)
