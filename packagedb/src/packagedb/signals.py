#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from packagedb.models import Package


@receiver(post_save, sender=Package)
def update_search_vector(sender, instance, **kwargs):
    Package.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('namespace', 'name', 'version', 'download_url')
    )
