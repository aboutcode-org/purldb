#
# Copyright (c) nexB Inc. and others. All rights reserved.
#
# ClearCode is a free software tool from nexB Inc. and others.
# Visit https://github.com/nexB/clearcode-toolkit/ for support and download.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
from collections import defaultdict
from hashlib import sha512
from pathlib import Path

from django.db.models import Q

import requests
from git import Repo
from packageurl import PackageURL

from clearcode.cdutils import Coordinate
from clearcode.cdutils import str2coord
from clearcode.models import CDitem

"""
The input is a bunch of scans from ClearlyDefined and
the output is a bunch of git repositories with commited and
pushed scans such that we balance the scans roughly evenly accross
different repositories.

The primary reason for multiple repositories is size of a single
repo. There is a size limit of 5 GB at GitHub and it's difficult
to work with repositories with million files.

Therefore the approach is to use hashing as a way to name git
repositories and directories. We compute hash on the purl of the scanned
package and use the first few layers of this hash for the repo and
directory names.

Initial processing steps are:
- We collect a list of scan and purl.
- For each we compute a hash and determine the repo and directory.
- If needed we create the repo or pull it.
- Then we store the scan using the purl hash and purl as path.
- Finally commit and push! : )

Because it's not practical to process many repos at once, we organize the
processing one repo a time. For this, we iterate over a bunch of records get or compute
the purl hash and process the records that share the same hash.

We are using a short hash that is three characters long using hexadecimal encoding.
Therefore we can have 16*16*16 = 4096 repositories where each repo would contain about
25k scan files, if we were to store 100 million scans (which is a high mark).
For reference one scan should use less than a 100k on average when compressed
with gzip or git based on looking at 15 million scans. Each repo should be roughly
couple hundred mega bytes big, based on 15 million scans.
"""

# Create hex values of integers and ignore the 0x prefix
repo_names = [hex(hash)[2:].zfill(3) for hash in range(4096)]


def store_scancode_scans_from_cd_items(work_dir, github_org="", count=0):
    """
    Iterate over CDItem objects with scancode scans.
    Save and commit them in git repositories in work dir.
    Process a maximum of count items and process all items if
    count is 0
    """
    cd_items = CDitem.objects.filter(~Q(content=b""), path__contains="tool/scancode")
    if count:
        cd_items = cd_items[:count]
    for purl_hash, cd_items in get_cd_item_by_purl_hash(cd_items=cd_items).items():
        commit_count = 0
        for cd_item in cd_items:
            data = cd_item.data
            cd_url = data.get("_metadata", {}).get("url")
            coordinate = Coordinate.from_dict(coords=str2coord(cd_url))
            if not is_valid_coordinate(coordinate):
                print(f"Invalid coordinate {coordinate}")
                continue
            scancode_scan = data.get("content")
            if not scancode_scan:
                continue
            repo = get_or_init_repo(
                repo_name=purl_hash,
                work_dir=work_dir,
                repo_namespace=github_org,
                user_name=github_org,
                pull=False,
            )
            purl = coordinate.to_purl()
            if add_scancode_scan(scancode_scan=scancode_scan, purl=purl, repo=repo):
                commit_count += 1
            if commit_count % 10 == 0:
                print(".", end="")
                origin = repo.remote(name="origin")
                origin.push()


def get_cd_item_by_purl_hash(cd_items):
    """Return a mapping of {purl_hash: [CDItem,....]}"""
    cd_item_by_purl_hash = defaultdict(list)
    for cd_item in cd_items:
        data = cd_item.data
        cd_url = data.get("_metadata", {}).get("url")
        coordinate = Coordinate.from_dict(coords=str2coord(cd_url))
        if not is_valid_coordinate(coordinate):
            print(f"Invalid coordinate {cd_url}")
            continue
        purl = coordinate.to_purl()
        purl_hash = get_purl_hash(purl=purl)
        cd_item_by_purl_hash[purl_hash].append(cd_item)
    return cd_item_by_purl_hash


def add_scancode_scan(repo, purl, scancode_scan):
    """
    Save and commit scancode scan for purl to git repo.
    Return true if we commited else false
    """
    purl_data_dir = get_or_create_dir_for_purl(purl=purl, repo=repo)
    scancode_scan_path = purl_data_dir / "scancode-toolkit-scan.json"
    with open(scancode_scan_path, "w") as f:
        json.dump(scancode_scan, f, indent=2)

    if repo.is_dirty():
        repo.index.add([scancode_scan_path])
        repo.index.commit(message=f"Add scancode-toolkit scan for {purl}")
        return True


def is_valid_coordinate(coordinate):
    return coordinate.type and coordinate.name and coordinate.version


def get_or_create_dir_for_purl(purl, repo):
    """
    Return a path to a directory for this purl,
    in this git repo.
    """
    purl_dir = repo.working_dir / get_purl_path(purl)
    purl_dir.mkdir(parents=True, exist_ok=True)
    return purl_dir


def get_purl_path(purl):
    purl_path = Path(purl.type)
    if purl.namespace:
        purl_path = purl_path / purl.namespace
    return purl_path / purl.name / purl.version


def get_purl_hash(purl: PackageURL, length: int = 3) -> str:
    """Return a short lower cased hash of a purl."""
    # This function takes a PackageURL object and an optional length parameter.
    # It returns a short hash of the purl. The length of the hash is determined by the length parameter.
    # The default length is 3. The function first converts the purl to bytes and then computes the sha512 hash of the purl.
    # It then takes the first 'length' characters of the hash and returns it in lower case.

    purl_bytes = str(purl).encode("utf-8")
    short_hash = sha512(purl_bytes).hexdigest()[:length]
    return short_hash.lower()


def get_or_init_repo(
    repo_name: str,
    work_dir: Path,
    repo_namespace: str = "",
    user_name: str = "",
    pull=False,
):
    """
    Return a repo object for repo name and namespace
    and store it in the work dir. Clone if it does not
    exist optionally take the latest pull if it does exist.
    """
    # TODO: Manage org repo name
    # MAYBE: CREATE ALL THE REPOS AT A TIME AND CLONE THEM LOCALLY
    if repo_name not in get_github_repos(user_name=user_name):
        repo_url = create_github_repo(repo_name=repo_name)
    repo_path = work_dir / repo_name
    if repo_path.exists():
        repo = Repo(repo_path)
        if pull:
            repo.origin.pull()
    else:
        repo = Repo.clone_from(repo_url, repo_path)
    return repo


def get_scan_download_url(
    namespace: str, purl: str, scan_file_name: str = "scancode-toolkit-scan.json"
):
    purl_hash = get_purl_hash(purl=purl)
    purl_path = get_purl_path(purl)
    return f"https://raw.githubusercontent.com/{namespace}/{purl_hash}/main/{purl_path}/{scan_file_name}"


def create_github_repo(repo_name, token=os.getenv("GH_TOKEN")):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    data = {
        "name": repo_name,
    }

    url = "https://api.github.com/user/repos"

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        print(f"Repository '{repo_name}' created successfully!")
    else:
        print(f"Failed to create repository. Status code: {response.status_code}")
        print(response.text)


def get_github_repos(user_name, token=os.getenv("GH_TOKEN")):
    """
    Yield full repo names for a user or org name, use the optional ``token`` if provided.
    Full repo name is in the form user or org name / repo name
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/users/{user_name}/repos"
    response = requests.get(url, headers=headers)

    # TODO: We need have a way to handle failures from GH API
    if not response.status_code == 200:
        raise Exception(
            f"HTTP {response.status_code}: Failed to get repos for {user_name}"
        )

    data = response.json()
    for repo_data in data:
        full_repo_name = repo_data.get("full_name")
        if full_repo_name:
            yield full_repo_name
