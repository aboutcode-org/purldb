# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-23 19:11
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('packagedb', '0015_remove_package_download_checksums'),
    ]

    operations = [
        migrations.RenameField(
            model_name='package',
            old_name='sha1',
            new_name='download_sha1',
        ),
    ]