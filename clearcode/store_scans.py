# -*- coding: utf-8 -*-
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

from clearcode.models import CDitem
from clearcode.cdutils import Coordinate
from clearcode.cdutils import str2coord
from django.db.models import Q
from hashlib import sha512
import json
from packageurl import PackageURL
from pathlib import Path
from git import Repo

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

repo_names = [hex(hash)[2:].zfill(3) for hash in range(4096)]

def store_scancode_scans_from_cd_items(work_dir, github_org="", count=0):
    """
    Iterate over CDItem objects with scancode scans.  
    Save and commit them in git repositories in work dir
    """
    cd_items = CDitem.objects.filter(~Q(content=b''), path__contains="tool/scancode")
    x = get_cd_item_by_repo_name(cd_items=cd_items)
    print(x)
    for repo_name, cd_items in x.items():
        for cd_item in cd_items:
            data = cd_item.data
            cd_url = data.get("_metadata", {}).get("url")
            coordinate = Coordinate.from_dict(coords=str2coord(cd_url))
            if not is_valid_coordinate(coordinate):
                #TODO: this is a bug, we need to log it
                continue
            purl = coordinate.to_purl()
            # temporary hack iterate on all hashes until we store 
            # hashes in CDItem
            if repo_name!=get_repo_name(purl):
                continue
            # Initialize the repo - Get or Create the git repo
            repo = get_or_init_repo(repo_name=repo_name, work_dir=work_dir, github_org=github_org)
            scancode_scan = data.get("content")
            if scancode_scan:
                add_scancode_scan(scancode_scan, purl, repo)
                # TODO: push for every 10 commits


def get_cd_item_by_repo_name(cd_items):
    cd_item_by_repo_name = {}
    for cd_item in cd_items:
        data = cd_item.data
        cd_url = data.get("_metadata", {}).get("url")
        coordinate = Coordinate.from_dict(coords=str2coord(cd_url))
        if not is_valid_coordinate(coordinate):
            #TODO: this is a bug, we need to log it
            continue
        purl = coordinate.to_purl()
        repo_name = get_repo_name(purl=purl)
        if cd_item_by_repo_name.get(repo_name):
            cd_item_by_repo_name[repo_name].append(cd_item)
        else:
            cd_item_by_repo_name[repo_name] = [cd_item]
    return cd_item_by_repo_name


def add_scancode_scan(scancode_scan, purl, repo):
    """
    Save and commit scancode scan for purl to git repo.
    """
    purl_data_dir = get_or_create_dir_for_purl(purl=purl, repo=repo)
    scancode_scan_path = purl_data_dir / "scancode-toolkit-scan.json"
    with open(scancode_scan_path, "w") as f:
        json.dump(scancode_scan,f,indent=2)
    repo.index.add([scancode_scan_path])
    repo.index.commit(message=f"Add scancode-toolkit scan for {purl}")


def is_valid_coordinate(coordinate):
    return coordinate.type and coordinate.name


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


def get_repo_name(purl: PackageURL, length: int=3) -> str:
    """
    Return a short lower cased hash of a purl.
    """
    #TODO: document this function in great detail, this is a part of spec
    purl_bytes = str(purl).encode("utf-8")
    short_hash = sha512(purl_bytes).hexdigest()[:length]
    return short_hash.lower()


# def run(directory, repo_url):
#     try:
#         repo = Repo.clone_from(repo_url, directory)
#     except:
#         repo = Repo(directory)
#         if repo.remotes.origin.fetch()[0].commit != repo.head.commit:
#             # Pull the latest changes from the remote repository
#             repo.remotes.origin.pull()

#     store_scancode_scans_from_cd_items(work_dir = directory)
#     RepoAdder.add_all(repo)
#     RepoCommiter.commit(repo=repo, message="Push")


def get_or_init_repo(repo_name: str, work_dir: Path, github_org: str= "", pull=False):
    # TODO: Check if repo exists on remote
    # TODO: If not exisiting on remote, create it on github_org
    """If exists take a clone in the working directory, if repo already exists in working directory
    then take the latest pull. Return the repo object"""
    repo_path = work_dir / repo_name
    if repo_path.exists():
        return Repo(repo_path)
    else:
        repo = Repo.init(repo_path)
        return repo


def get_scan_download_url(purl:str, github_org:str, scan_file_name: str = "scancode-toolkit-scan.json"):
    repo_name = get_repo_name(purl=purl)
    purl_path = get_purl_path(purl)
    return f"https://raw.githubusercontent.com/{github_org}/{repo_name}/main/{purl_path}/{scan_file_name}"


if __name__ == "__main__":
    work_dir = Path("")
    store_scancode_scans_from_cd_items(work_dir=work_dir, github_org="TG1999", count=5)
