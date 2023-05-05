#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.conf.urls import include
from django.urls import re_path
from django.views.generic import RedirectView
from rest_framework import routers

from clearcode.api import CDitemViewSet
from packagedb.api import PackageViewSet
from packagedb.api import ResourceViewSet
from matchcode.api import ApproximateDirectoryContentIndexViewSet
from matchcode.api import ApproximateDirectoryStructureIndexViewSet
from matchcode.api import ExactFileIndexViewSet
from matchcode.api import ExactPackageArchiveIndexViewSet
from minecode.api import PriorityResourceURIViewSet


api_router = routers.DefaultRouter()
api_router.register(r'packages', PackageViewSet)
api_router.register(r'resources', ResourceViewSet)
api_router.register(r'approximate_directory_content_index', ApproximateDirectoryContentIndexViewSet)
api_router.register(r'approximate_directory_structure_index', ApproximateDirectoryStructureIndexViewSet)
api_router.register(r'exact_file_index', ExactFileIndexViewSet)
api_router.register(r'exact_package_archive_index', ExactPackageArchiveIndexViewSet)
api_router.register(r'cditems', CDitemViewSet, 'cditems')
api_router.register(r'on_demand_queue', PriorityResourceURIViewSet)

urlpatterns = [
    re_path(r'^api/', include((api_router.urls, 'api'))),
    re_path("", RedirectView.as_view(url="api/")),
]
