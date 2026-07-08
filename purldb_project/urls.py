#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.conf import settings
from django.conf.urls import include
from django.urls import path
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView

from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework import routers

from matchcode.api import ApproximateDirectoryContentIndexViewSet
from matchcode.api import ApproximateDirectoryStructureIndexViewSet
from minecode.api import ScannableURIViewSet
from minecode.api import index_package_scan
from packagedb.api import CollectViewSet
from packagedb.api import PackageActivityListenerView
from packagedb.api import PackageActivityViewSet
from packagedb.api import PackageSetViewSet
from packagedb.api import PackageUpdateSet
from packagedb.api import PackageViewSet
from packagedb.api import PackageWatchViewSet
from packagedb.api import PurlValidateViewSet
from packagedb.api import ResourceViewSet
from packagedb.from_purl import api_from_purl_router
from packagedb.to_purl import api_to_purl_router

api_router = routers.DefaultRouter()
api_router.register("packages", PackageViewSet)
api_router.register("update_packages", PackageUpdateSet, "update_packages")
api_router.register("package_sets", PackageSetViewSet)
api_router.register("resources", ResourceViewSet)
api_router.register("validate", PurlValidateViewSet, "validate")
api_router.register("collect", CollectViewSet, "collect")
api_router.register("watch", PackageWatchViewSet)
api_router.register("scan_queue", ScannableURIViewSet)
api_router.register("approximate_directory_content_index", ApproximateDirectoryContentIndexViewSet)
api_router.register(
    "approximate_directory_structure_index", ApproximateDirectoryStructureIndexViewSet
)
api_router.register("package_activity", PackageActivityViewSet)


urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("api/", include((api_router.urls, "api"))),
    path("api/to_purl/", include((api_to_purl_router.urls, "api_to"))),
    path("api/from_purl/", include((api_from_purl_router.urls, "api_from"))),
    path("", include("packagedb.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/scan_queue/index_package_scan/<str:key>/",
        index_package_scan,
        name="index_package_scan",
    ),
]


# Endpoint to receive updates related to subscribed packages
urlpatterns.append(
    path(
        "api/users/@purldb/inbox",
        PackageActivityListenerView.as_view(),
        name="package_activity_listener",
    ),
)

if settings.DEBUG and settings.DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
