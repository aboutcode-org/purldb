# Generated by Django 5.1.2 on 2024-12-05 00:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("packagedb", "0087_rename_discovered_dependency_attribute"),
    ]

    operations = [
        migrations.AlterField(
            model_name="package",
            name="md5",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="MD5 checksum hex-encoded, as in md5sum.",
                max_length=32,
                null=True,
                verbose_name="MD5",
            ),
        ),
        migrations.AlterField(
            model_name="package",
            name="sha1",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA1 checksum hex-encoded, as in sha1sum.",
                max_length=40,
                null=True,
                verbose_name="SHA1",
            ),
        ),
        migrations.AlterField(
            model_name="package",
            name="sha256",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA256 checksum hex-encoded, as in sha256sum.",
                max_length=64,
                null=True,
                verbose_name="SHA256",
            ),
        ),
        migrations.AlterField(
            model_name="package",
            name="sha512",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA512 checksum hex-encoded, as in sha512sum.",
                max_length=128,
                null=True,
                verbose_name="SHA512",
            ),
        ),
        migrations.AlterField(
            model_name="resource",
            name="md5",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="MD5 checksum hex-encoded, as in md5sum.",
                max_length=32,
                null=True,
                verbose_name="MD5",
            ),
        ),
        migrations.AlterField(
            model_name="resource",
            name="sha1",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA1 checksum hex-encoded, as in sha1sum.",
                max_length=40,
                null=True,
                verbose_name="SHA1",
            ),
        ),
        migrations.AlterField(
            model_name="resource",
            name="sha256",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA256 checksum hex-encoded, as in sha256sum.",
                max_length=64,
                null=True,
                verbose_name="SHA256",
            ),
        ),
        migrations.AlterField(
            model_name="resource",
            name="sha512",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA512 checksum hex-encoded, as in sha512sum.",
                max_length=128,
                null=True,
                verbose_name="SHA512",
            ),
        ),
    ]
