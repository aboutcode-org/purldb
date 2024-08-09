#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import pkgutil


class Mapper(object):
    """
    Abstract base class for mappers. Subclasses must implement the
    get_packages() method and use a routing decorator for the URIs they can
    handle.
    """
    def __call__(self, uri, resource_uri):
        # Note: we let exceptions bubble up and they will be caught and
        # processed by the worker loop
        return self.get_packages(uri, resource_uri)

    def get_packages(self, uri, resource_uri):
        """
        This method must yield ScannedPackage objects (or return a list) built
        from a resource_uri ResourceURI object.
        """
        raise NotImplementedError


"""
Minimal way to recursively import all submodules dynamically. If this module is
imported, all submodules will be imported: this triggers the actual registration
of mappers. This should stay as the last import in this init module.
"""
for _, name, _ in pkgutil.walk_packages(__path__, prefix=__name__ + '.'):
    __import__(name)
