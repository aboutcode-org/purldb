# Generated by Django 5.1.5 on 2025-05-29 23:08

from django.db import migrations


def set_package_content_value(apps, schema_editor):
    from packagedb.models import PackageContentType

    Package = apps.get_model("packagedb", "Package")
    packages = Package.objects.filter(type="pypi", package_content__isnull=True).iterator(chunk_size=5000)

    source_extensions = (".tar.gz", ".zip", ".tar.bz2", ".tar.xz", ".tar.Z", ".tgz", ".tbz")
    binary_extensions = (".whl", ".egg")
    unsaved_packages = []
    for i, package in enumerate(packages, start=1):
        if not i % 5000:
            Package.objects.bulk_update(
                objs=unsaved_packages,
                fields=[
                    "package_content",
                ]
            )
            unsaved_packages = []

        name = package.filename if package.filename else package.download_url
        if name.endswith(source_extensions):
            package.package_content = PackageContentType.SOURCE_ARCHIVE
        if name.endswith(binary_extensions):
            package.package_content = PackageContentType.BINARY
        if package.package_content:
            unsaved_packages.append(package)

    if unsaved_packages:
        Package.objects.bulk_update(
            objs=unsaved_packages,
            fields=["package_content"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("packagedb", "0092_alter_party_email_alter_party_name"),
    ]

    operations = [
        migrations.RunPython(
            set_package_content_value,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
