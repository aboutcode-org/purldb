#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


class PackageDBRouter:
    app_labels = [
        "clearcode",
        "clearindex",
        "minecode",
        "matchcode",
        "packagedb",
    ]

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.app_labels:
            return "packagedb"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.app_labels:
            return "packagedb"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.app_labels
            or obj2._meta.app_label in self.app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.app_labels:
            return db == "packagedb"
        return None


class ScancodeIORouter:
    app_labels = [
        "scanpipe",
    ]

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.app_labels:
            return "default"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.app_labels:
            return "default"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.app_labels
            or obj2._meta.app_label in self.app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.app_labels:
            return db == "default"
        return None
