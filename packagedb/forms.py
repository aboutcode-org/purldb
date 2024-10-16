#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django import forms


class PackageSearchForm(forms.Form):
    search = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "pkg:maven/org.elasticsearch/elasticsearch@7.17.9?classifier=sources"
            },
        ),
    )
