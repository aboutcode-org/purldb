#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.urls import path
from rest_framework.routers import DefaultRouter
from django.views.generic import RedirectView
from packagedb.views import PackageListView
from packagedb.views import PackageDetailView

router = DefaultRouter()
router.register(r"packages", PackageListView, basename="package")

urlpatterns = [
    path("", RedirectView.as_view(url="/packages")),
    path("packages/", PackageListView.as_view(), name='package_list'),
    path("packages/<uuid:uuid>/", PackageDetailView.as_view(), name='package_detail'),
]
