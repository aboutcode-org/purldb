#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from django.conf.urls import include
from django.urls import re_path

from packagedbio import urls as packagedb_urls


urlpatterns = [
    re_path(r'^api/', include((packagedb_urls.api_router.urls, 'api'))),
]
