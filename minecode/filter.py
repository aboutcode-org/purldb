#!/usr/bin/env python
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import csv
import string

from minecode import version


def sf_net(input_file, output):
    """
    Take an input_file CSV file and writes and output CSV file,
    adding new columns and trying to sf_net the data
    """
    download_url_template = (
        "http://master.dl.sourceforge.net/project/%(project_id)s%(filename)s"
    )

    existing_headers = (
        "external_id,name,version,license,owners,"
        "homepage_url,keywords,description".split(",")
    )

    new_headers = (
        "computed_version,release_date_ts,file_download_url,"
        "reviewed,curated_name,excluded_reason,curated_owner,"
        "owner_type".split(",")
    )

    with open(output, "w") as fo:
        writer = csv.writer(fo, quoting=csv.QUOTE_ALL)
        with open(input_file) as fi:
            reader = csv.reader(fi)
            for i, row in enumerate(reader):
                if i == 0:
                    # add headers on first row
                    row.extend(new_headers)
                if not row:
                    continue
                project_id = row[0]
                name = row[1]
                version_column = row[2]
                sep = ":  released on "
                if sep not in version_column:
                    # write as is if we do not have a file release date
                    # separator
                    writer.writerow(row)
                    continue
                filename, release_date_ts = version_column.split(sep, 1)
                found_version = version.version_hint(filename)
                row.append(found_version or "")
                row.append(release_date_ts or "")
                row.append(download_url_template % locals())
                row.append("")  # reviewed
                row.append("")  # curated name
                excluded_reason = ""
                if "." in project_id:
                    excluded_reason = "mirror or special project"
                elif not found_version:
                    excluded_reason = "no version"
                elif not good_name(name):
                    excluded_reason = "special chars in name"
                elif not good_filename(project_id, filename, name):
                    excluded_reason = "multi component possible"
                row.append(excluded_reason)
                row.append("")  # curated_owner
                row.append("")  # owner_type
                writer.writerow(row)


def good_name(s):
    """
    Tom: about the "discarding" rules for sf.net dataset here is what I have in
    mind beyond the the discarding you already did (i.e. harvest)

    -project name, discard if:
    -- there is a punctuation sign string.punctuation
    -- there is non-ascii letters string.letters + string.digit
    """
    return (
        s
        and all(c not in string.punctuation for c in s)
        and all(c in string.ascii_lowercase for c in s.lower())
    )


def good_filename(pid, fn, name):
    """
    filename, discard if the project id or name is not contained entirely in
    the filename (possible multi components for this project)
    """
    return fn and (pid.lower() in fn.lower() or name.lower() in fn.lower())
