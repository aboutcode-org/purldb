#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import os
import saneyaml

from pathlib import Path

from aboutcode import hashid
from packageurl import PackageURL
from scanpipe.pipes import federatedcode


def write_packageurls_to_file(repo, base_dir, packageurls):
    purl_file_rel_path = os.path.join(base_dir, hashid.PURLS_FILENAME)
    purl_file_full_path = Path(repo.working_dir) / purl_file_rel_path
    write_data_to_file(path=purl_file_full_path, data=packageurls)
    return purl_file_rel_path


def write_data_to_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))


def write_purls_to_repo(repo, package, packages, push_commit=False):
    # save purls to yaml
    path_elements = hashid.package_path_elements(package)
    _, core_path, _, _ = path_elements
    ppath = core_path / hashid.PURLS_FILENAME
    purls = [p.purl for p in packages]
    federatedcode.write_data_as_yaml(
        base_path=repo.working_dir,
        file_path=ppath,
        data=purls,
    )

    change_type = "Add" if ppath in repo.untracked_files else "Update"
    commit_message = f"""\
    {change_type} list of available {package} versions
    """
    federatedcode.commit_changes(
        repo=repo,
        files_to_commit=[ppath],
        commit_message=commit_message,
    )

    # see if we should push
    if push_commit:
        federatedcode.push_changes(repo=repo)
