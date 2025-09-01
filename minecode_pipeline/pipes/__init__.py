#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from aboutcode import hashid
from scanpipe.pipes import federatedcode


def write_purls_to_repo(repo, package, packages, push_commit=False):
    # save purls to yaml
    ppath = hashid.get_package_purls_yml_file_path(package)
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
