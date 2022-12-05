# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
#
# ClearCode is a free software tool from nexB Inc. and others.
# Visit https://github.com/nexB/clearcode-toolkit/ for support and download.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import base64

from django.urls import include, re_path
from rest_framework import routers
from rest_framework import serializers
from rest_framework import viewsets

from clearcode.models import CDitem


class CDitemContentFieldSerializer(serializers.Field):
    """
    Custom Field Serializer used to translate between Django ORM binary field and
    base64-encoded string
    """
    def to_representation(self, obj):
        return base64.b64encode(obj).decode('utf-8')

    def to_internal_value(self, data):
        return base64.b64decode(data)


class CDitemSerializer(serializers.HyperlinkedModelSerializer):
    """
    Custom Serializer used to serialize the CDitem model
    """
    content = CDitemContentFieldSerializer(required=False)
    class Meta:
        model = CDitem
        fields = (
            'path',
            'uuid',
            'content',
            'last_modified_date',
            'last_map_date',
            'map_error',
        )


class CDitemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows CDitems to be viewed.
    """
    serializer_class = CDitemSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        last_modified_date = self.request.query_params.get('last_modified_date', None)
        queryset = CDitem.objects.all()

        if last_modified_date:
            queryset = CDitem.objects.modified_after(last_modified_date)

        return queryset


router = routers.DefaultRouter()
router.register(r'cditems', CDitemViewSet, 'cditems')

urlpatterns = [
    re_path('^api/', include((router.urls, 'api'))),
]
