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
from matchcode.api import D2DViewSet
from matchcode.api import MatchingViewSet
from matchcode.api import RunViewSet
from minecode.api import ScannableURIViewSet
from minecode.api import index_package_scan
from packagedb.api import CollectViewSet
from packagedb.api import HealthViewSet
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


#
# A class to "document" the main "API root" web page.
# Inspired by https://stackoverflow.com/questions/17496249/in-django-restframework-how-to-change-the-api-root-documentation
#
class PurldbAPI(routers.APIRootView):
    """
    AboutCode's PurlDB provide easy access to live, precomputed and cached data
    about open source software packages origin, license, health, security, and
    other attributes, by passing a Package-URL (PURL). PURL is the standard
    package identifier used in SBOMs, vulnerability databases and across
    software supply chains.

    You can select a PurlDB JSON API endpoint below to navigate the live API, or
    use the links above to access to the Swagger/OpenAPI actionable API
    documentation, or the main PurlDB guids and documentation.
    """

    pass


class PurlDbRouter(routers.DefaultRouter):
    APIRootView = PurldbAPI


api_router = PurlDbRouter()
# Empty REST_API_ENDPOINTS → register everything; otherwise only listed prefixes.
_allowed = settings.REST_API_ENDPOINTS


def register(prefix, viewset, basename=None):
    if _allowed and prefix not in _allowed:
        return
    if basename:
        api_router.register(prefix, viewset, basename)
    else:
        api_router.register(prefix, viewset)


register("packages", PackageViewSet)
register("resources", ResourceViewSet)
register("validate", PurlValidateViewSet, "validate")
register("health", HealthViewSet, "health")
register("scan_queue", ScannableURIViewSet)

if not settings.PURLDB_PUBLIC_SETUP:
    register("update_packages", PackageUpdateSet, "update_packages")
    register("package_sets", PackageSetViewSet)
    register("collect", CollectViewSet, "collect")
    register("watch", PackageWatchViewSet)
    register("approximate_directory_content_index", ApproximateDirectoryContentIndexViewSet)
    register("approximate_directory_structure_index", ApproximateDirectoryStructureIndexViewSet)
    register("package_activity", PackageActivityViewSet)
    register("matching", MatchingViewSet, "matching")
    register("d2d", D2DViewSet, "d2d")
    register("runs", RunViewSet)

urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("api/", include((api_router.urls, "api"))),
    path("api/to_purl/", include((api_to_purl_router.urls, "api_to"))),
    path("api/from_purl/", include((api_from_purl_router.urls, "api_from"))),
    path("", RedirectView.as_view(url="api/")),
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
