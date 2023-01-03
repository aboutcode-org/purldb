#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from rest_framework.pagination import PageNumberPagination


class PageSizePagination(PageNumberPagination):
    """
    Adds the page_size parameter. Default results per page is 10.
    A page_size parameter can be provided, limited to 100 results per page max.
    For example:
    http://api.example.org/accounts/?page=4&page_size=100
    """
    page_size = 10
    max_page_size = 100
    page_size_query_param = 'page_size'
