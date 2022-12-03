#
# Copyright (c) nexB Inc. http://www.nexb.com/ - All rights reserved.
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
