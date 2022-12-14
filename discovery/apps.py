#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DiscoveryConfig(AppConfig):
    name = 'discovery'
    verbose_name = _('Discovery')
