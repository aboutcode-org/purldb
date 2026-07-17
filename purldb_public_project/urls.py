#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.conf.urls import include
from django.urls import path
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView

from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework import routers

from packagedb.api import PackagePublicViewSet
from packagedb.api import PurlValidateViewSet
from packagedb.api import ResourceViewSet

api_router = routers.DefaultRouter()
api_router.register("packages", PackagePublicViewSet)
api_router.register("resources", ResourceViewSet)
api_router.register("validate", PurlValidateViewSet, "validate")


urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("api/", include((api_router.urls, "api"))),
    path("", RedirectView.as_view(url="api/")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
