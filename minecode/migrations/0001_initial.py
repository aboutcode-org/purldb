# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ResourceURI',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uri', models.CharField(max_length=2048, db_index=True)),
                ('canonical', models.CharField(unique=True, max_length=3000)),
                ('rank', models.PositiveIntegerField(help_text='Indicates the relative rank of an URL inside a domain (such as the highest ranking project on sourceforge would be rank 1). Several URI may have the same rank, even inside the same domain.', null=True, db_index=True, blank=True)),
                ('priority', models.PositiveIntegerField(default=0, help_text='Indicates the absolute priority of a URI (default to zero), higher number means higher priority, zero means lowest priority.', db_index=True)),
                ('last_visit_date', models.DateTimeField(help_text='Timestamp set to the date of the last visit.', null=True, db_index=True, blank=True)),
                ('wip_date', models.DateTimeField(help_text='Work In Progress. Timestamp sets at the start of a visit or mapping or null when nothing is in progress.', null=True, db_index=True, blank=True)),
                ('last_modified_date', models.DateTimeField(help_text='Timestamp set to the last modified date of the remote Resource, such as the modified date of a file, the lastmod value on a sitemap or the modified date returned by an HTTP resource.', null=True, db_index=True, blank=True)),
                ('file_name', models.CharField(help_text='File name of a Resource sometimes part of the URI properand sometimes only available through an HTTP header.', max_length=255, null=True, db_index=True, blank=True)),
                ('size', models.PositiveIntegerField(help_text='Size in bytes.', null=True, db_index=True, blank=True)),
                ('sha1', models.CharField(help_text='SHA1 checksum hex-encoded, as in sha1sum.', max_length=40, null=True, db_index=True, blank=True)),
                ('md5', models.CharField(help_text='MD5 checksum hex-encoded, as in md5sum.', max_length=32, null=True, db_index=True, blank=True)),
                ('sig', models.TextField(help_text='PGP signature, such as an asc file at Apache.', null=True, blank=True)),
                ('data', models.TextField(help_text='Contains the data that was fetched/extracted from a URI.', blank=True)),
                ('error', models.TextField(help_text='Stores processing errors messages and diagnostics details.', blank=True)),
            ],
            options={
                'ordering': ['-priority', 'uri'],
                'verbose_name': 'Resource URI',
            },
        ),
    ]
