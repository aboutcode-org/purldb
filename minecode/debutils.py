#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#



def parse_email(text):
    """
    Return a tuple of (name, email) extracted from a `text` string.
        Debian TeX Maintainers <debian-tex-maint@lists.debian.org>
    """
    if not text:
        return None, None
    name, _, email = text.partition('<')
    name = name.strip()
    email = email.strip()
    if not email:
        return name, email
    email.strip('>')
    return name, email


def comma_separated(text):
    """
    Return a list of strings from a comma-separated text.
    """
    if not text:
        return []
    return [t.strip() for t in text.split(',') if t and t.strip()]


def fold(value):
    """
    Return a folded `value` string.
    """
    if not value:
        return value
    return ''.join(value.split())


def line_separated(value):
    """
    Return a list of values from a `value` string using line delimiters.
    """
    if not value:
        return []
    return [v.strip() for v in value.splitlines(False) if v]
