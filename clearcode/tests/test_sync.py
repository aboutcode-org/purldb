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

import gzip
import json

from django.test import TestCase

from clearcode.models import CDitem
from clearcode.sync import db_saver


class SyncDbsaverTestCase(TestCase):
    def setUp(self):
        self.test_path = "composer/packagist/yoast/wordpress-seo/revision/9.5-RC3.json"
        self.test_content = {"test": "content"}

        self.cditem0 = CDitem.objects.create(
            path=self.test_path,
            content=gzip.compress(json.dumps(self.test_content).encode("utf-8")),
        )

    def test_db_saver_identical_path(self):
        db_saver(content=self.test_content, blob_path=self.test_path)
        self.assertEqual(1, len(CDitem.objects.all()))

    def test_db_saver_different_path(self):
        db_saver(content=self.test_content, blob_path="new/blob/path.json")
        self.assertEqual(2, len(CDitem.objects.all()))
