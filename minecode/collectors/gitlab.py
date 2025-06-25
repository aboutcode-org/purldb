#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging

import requests


"""
Collect gitlab packages from gitlab registries.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def gitlab_get_all_package_version_author(subset_path):
    """
    Return a list of all version numbers along with author and author email
    for the package.
    """
    repo_tags = f"https://gitlab.com/api/v4/projects/{subset_path}/repository/tags"
    try:
        response = requests.get(repo_tags)
        response.raise_for_status()
        data = response.json()
        version_author_list = []
        # Get all available versions
        for item in data:
            version = item["name"]
            author = item["commit"]["author_name"]
            author_email = item["commit"]["author_email"]
            version_author_list.append((version, author, author_email))
        return version_author_list
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")
