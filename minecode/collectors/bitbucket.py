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
Collect bitbucket packages from bitbucket registries.
"""

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def bitbucket_get_all_package_version_author(subset_path):
    """
    Return a list of all version numbers along with author for the package.
    """
    repo_tags = f"https://api.bitbucket.org/2.0/repositories/{subset_path}/refs/tags"
    version_author_list = []
    try:
        while repo_tags:
            response = requests.get(repo_tags)
            response.raise_for_status()
            data = response.json()
            if data["size"] > 0:
                # Get all available versions
                for item in data["values"]:
                    version = item.get("name")
                    target = item.get("target") or {}
                    author = target.get("author") or {}
                    if author.get("type") == "author":
                        user = author.get("user") or {}
                        author_display_name = user.get("display_name")
                    version_author_list.append((version, author_display_name))
            # Handle pagination
            repo_tags = data.get("next", None)
        return version_author_list
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error occurred: {err}")
