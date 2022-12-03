#
# Copyright (c) 2016 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from django.conf.urls import include
from django.urls import re_path

from packagedb.api import PackageViewSet
from packagedb.api import ResourceViewSet
from rest_framework import routers

from matchcode.api import ApproximateDirectoryContentIndexViewSet
from matchcode.api import ApproximateDirectoryStructureIndexViewSet
from matchcode.api import ExactFileIndexViewSet
from matchcode.api import ExactPackageArchiveIndexViewSet


api_router = routers.DefaultRouter()
api_router.register(r'packages', PackageViewSet)
api_router.register(r'resources', ResourceViewSet)
api_router.register(r'approximate_directory_content_index', ApproximateDirectoryContentIndexViewSet)
api_router.register(r'approximate_directory_structure_index', ApproximateDirectoryStructureIndexViewSet)
api_router.register(r'exact_file_index', ExactFileIndexViewSet)
api_router.register(r'exact_package_archive_index', ExactPackageArchiveIndexViewSet)

urlpatterns = [
    re_path(r'^api/', include((api_router.urls, 'api'))),
]
