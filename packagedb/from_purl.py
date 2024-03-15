#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import routers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from packagedb.find_source_repo import get_package_object_from_purl
from packagedb.find_source_repo import get_source_repo
from packagedb.serializers import PurltoGitRepoResponseSerializer
from packagedb.serializers import PurltoGitRepoSerializer


@extend_schema(
    parameters=[
        OpenApiParameter("package_url", str, "query", description="package url"),
    ],
    responses={200: PurltoGitRepoResponseSerializer()},
)
class FromPurlToGitRepoViewSet(viewsets.ViewSet):
    """
    Return a ``golang_purl`` from a standard go import string or
    a go.mod string ``go_package``.

    For example:

        >>> get_golang_purl("github.com/gorilla/mux v1.8.1")
        "pkg:golang/github.com/gorilla/mux@v1.8.1"
        >>> # This is an example of go.mod string `package version`
        >>>
        >>> get_golang_purl("github.com/gorilla/mux")
        "pkg:golang/github.com/gorilla/mux"
        >>> #This is an example a go import string `package`
    """

    serializer_class = PurltoGitRepoSerializer

    def get_view_name(self):
        return "Purl2Git"

    def list(self, request):
        serializer = self.serializer_class(data=request.query_params)
        response = {}

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        package_url = validated_data.get("package_url")
        package = get_package_object_from_purl(package_url=package_url)
        if not package:
            return Response(
                {"errors": f"{package_url} does not exist in this database"},
                status=status.HTTP_404_NOT_FOUND,
            )
        source_repo = get_source_repo(package=package)
        response["git_repo"] = str(source_repo)
        serializer = PurltoGitRepoResponseSerializer(
            response, context={"request": request}
        )
        return Response(serializer.data)


api_from_purl_router = routers.DefaultRouter()
api_from_purl_router.register("purl2git", FromPurlToGitRepoViewSet, "purl2git")
