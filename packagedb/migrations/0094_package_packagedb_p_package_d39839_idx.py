# Generated by Django 5.1.5 on 2025-06-10 22:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("packagedb", "0093_update_pypi_package_content"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="package",
            index=models.Index(
                fields=["package_content"], name="packagedb_p_package_d39839_idx"
            ),
        ),
    ]
