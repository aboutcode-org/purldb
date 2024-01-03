#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.urls import include
from django.urls import path
from django.views.generic import RedirectView
from rest_framework import routers

from matchcode_pipeline.api import MatchingViewSet
from scanpipe.api.views import RunViewSet


api_router = routers.DefaultRouter()
api_router.register('matching', MatchingViewSet, basename='matching')
api_router.register('runs', RunViewSet, basename='runs')

urlpatterns = [
    path('api/', include(api_router.urls)),
    path('', include('scanpipe.urls')),
    path('', RedirectView.as_view(url='api/')),
]
