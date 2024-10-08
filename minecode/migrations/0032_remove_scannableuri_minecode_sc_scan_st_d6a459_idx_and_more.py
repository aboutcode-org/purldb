# Generated by Django 5.0.1 on 2024-03-07 00:59

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("minecode", "0031_importableuri"),
        ("packagedb", "0083_delete_apiuser"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="scannableuri",
            name="minecode_sc_scan_st_d6a459_idx",
        ),
        migrations.RenameField(
            model_name="scannableuri",
            old_name="rescan_uri",
            new_name="reindex_uri",
        ),
        migrations.AlterUniqueTogether(
            name="scannableuri",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="scannableuri",
            name="pipelines",
            field=models.JSONField(
                blank=True,
                default=list,
                editable=False,
                help_text="A list of ScanCode.io pipeline names to be run for this scan",
            ),
        ),
        migrations.AddField(
            model_name="scannableuri",
            name="scan_date",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Timestamp set to the date when a scan was taken by a worker",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="scannableuri",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, null=True),
        ),
        migrations.AddIndex(
            model_name="scannableuri",
            index=models.Index(
                fields=["scan_status", "scan_date"],
                name="minecode_sc_scan_st_baab37_idx",
            ),
        ),
        migrations.RemoveField(
            model_name="scannableuri",
            name="last_status_poll_date",
        ),
        migrations.RemoveField(
            model_name="scannableuri",
            name="scan_request_date",
        ),
        migrations.RemoveField(
            model_name="scannableuri",
            name="scan_uuid",
        ),
    ]
