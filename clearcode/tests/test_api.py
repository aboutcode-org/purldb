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
import datetime
import gzip
import json

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from clearcode import api
from clearcode.models import CDitem


class CDitemSerializerTestCase(TestCase):

    def setUp(self):
        self.cditem_attributes = {
            'path': 'test/path/file.json',
            'content': gzip.compress(json.dumps({'test': 'content'}).encode('utf-8'))
        }
        self.cditem = CDitem.objects.create(**self.cditem_attributes)
        self.serializer = api.CDitemSerializer(instance=self.cditem)
        self.data = self.serializer.data

    def test_contains_expected_fields(self):
        self.assertCountEqual(self.data.keys(), ['path', 'uuid', 'content', 'last_modified_date', 'last_map_date', 'map_error'])

    def test_path_field_content(self):
        self.assertEqual(self.data['path'], self.cditem_attributes['path'])
    
    def test_content_field_content(self):
        decoded_test_data = base64.b64decode(self.data['content'])
        self.assertEqual(decoded_test_data, self.cditem_attributes['content'])
        self.assertEqual(json.loads(gzip.decompress(decoded_test_data)), {'test': 'content'})

    def test_last_map_date_field_content(self):
        self.assertIsNone(self.data['last_map_date'])

    def test_map_error_field_content(self):
        self.assertIsNone(self.data['map_error'])


class CDitemAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.test_path = 'test/path/file.json'

        self.post_test_path = 'test/post/path/file.json'
        
        self.test_data = {'test': 'content'}
        self.test_content = gzip.compress(json.dumps(self.test_data).encode('utf-8'))
        
        self.cditem = CDitem.objects.create(path=self.test_path)
        self.uuid = self.cditem.uuid

    def test_api_cditems_get(self):
        response = self.client.get('/api/cditems/{}/'.format(self.uuid))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('path'), self.test_path)
        self.assertEqual(response.data.get('uuid'), str(self.uuid))

    def test_api_cditems_get_list(self):
        response = self.client.get('/api/cditems/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

    def test_api_cditems_get_list_by_last_modified_date_old_date(self):
        test_date = datetime.datetime.now() - datetime.timedelta(days=1)
        test_date_string = '{}-{}-{}'.format(test_date.year, test_date.month, test_date.day)

        response = self.client.get('/api/cditems/?last_modified_date={}'.format(test_date_string))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data.get('count'))

    def test_api_cditems_get_list_by_last_modified_date_future(self):
        test_date = datetime.datetime.now() + datetime.timedelta(days=1)
        test_date_string = '{}-{}-{}'.format(test_date.year, test_date.month, test_date.day)

        response = self.client.get('/api/cditems/?last_modified_date={}'.format(test_date_string))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data.get('count'))
    
    def test_api_cditems_put(self):
        test_payload = {
            'path': self.test_path,
            'content': base64.b64encode(self.test_content).decode('utf-8')
        }

        response = self.client.put('/api/cditems/{}/'.format(self.uuid), test_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        cditem = CDitem.objects.get(path=self.test_path)
        self.assertEqual(cditem.data, self.test_data)
    
    def test_api_cditems_post(self):
        test_payload = {
            'path': self.post_test_path,
            'content': base64.b64encode(self.test_content).decode('utf-8')
        }

        response = self.client.post('/api/cditems/', test_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('path'), self.post_test_path)

        cditem = CDitem.objects.get(path=self.post_test_path)
        self.assertEqual(cditem.data, self.test_data)
