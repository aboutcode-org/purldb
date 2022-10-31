#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import importlib

try:
    # Python 2
    unicode = unicode  # NOQA
except NameError:  # pragma: nocover
    # Python 3
    unicode = str  # NOQA


class Seeder(object):
    """
    Abstract base class for seeding URIs to visit. Each visitor should create a
    subclass of Seeder and implement the get_seeds method to yield the top levle
    URIs required to bootstrap the visiting process. The framework decides waht
    to do with these seeds, but will typically ensure they exist as ResourceURIs
    in the DB. To be used, seeder classes must be added to the list of active
    Seeders in the settings module.
    """

    revisit_after = 240  # hours

    def get_seeds(self):
        """
        Yield seed URIs strings. Subclass must override.
        """
        raise NotImplementedError()


def get_active_seeders(seeders=()):
    """
    Return Seeder instance either from:
     - a provided list of Seeder subclasses or fully qualified class names.
     - the seeder classes configured as active in the settings or environment
       if no seeders are provided.
    """
    if not seeders:
        seeders = get_configured_seeders()
    for seeder in seeders:
        if isinstance(seeder, (bytes, unicode)):
            module_name, _, class_name = seeder.rpartition('.')
            module = importlib.import_module(module_name)
            yield getattr(module, class_name)()
        else:
            # assume this is a Seeder class and instantiate
            yield seeder()


def get_configured_seeders():
    """
    Return Seeder class qualified names referenced as active in the settings or
    environment.
    """
    from discovery.management.commands import get_settings
    # ACTIVE_VISITOR_SEEDS is a list of fully qualified Seeder subclass strings
    return get_settings('ACTIVE_SEEDERS') or []
