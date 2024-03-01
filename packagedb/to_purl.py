#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.db import router
from drf_spectacular.utils import OpenApiParameter, extend_schema
from packageurl.utils import get_golang_purl
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from packagedb.serializers import GoLangPurlResponseSerializer
from packagedb.serializers import GoLangPurlSerializer
from rest_framework import routers


@extend_schema(
    parameters=[
        OpenApiParameter("go_package", str, "query", description="go import package"),
    ],
    responses={200: GoLangPurlResponseSerializer()},
)
class GolangPurlViewSet(viewsets.ViewSet):

    serializer_class = GoLangPurlSerializer

    def get_view_name(self):
        return "GoLang purl"

    def list(self, request):
        serializer = self.serializer_class(data=request.query_params)
        response = {}

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        go_import = validated_data.get("go_package")
        purl = get_golang_purl(go_import)
        response["golang_purl"] = purl
        serializer = GoLangPurlResponseSerializer(
            response, context={"request": request}
        )
        return Response(serializer.data)

api_to_purl_router = routers.DefaultRouter()
api_to_purl_router.register("go", GolangPurlViewSet, "go")