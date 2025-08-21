#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import logging
import saneyaml
import shutil
import sys
import tempfile
import textwrap

from django.conf import settings

from aboutcode import hashid
from git import Repo

from minecode.management.commands import VerboseCommand


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

TRACE = False
if TRACE:
    logger.setLevel(logging.DEBUG)


WORKER_FUNCS = {}


class Command(VerboseCommand):
    help = "Run a visiting worker loop to collect package purls to files and commit to repo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            dest="repo",
            default=None,
            action="store_false",
            help="specify which repo to visit",
        )

    def handle(self, *args, **options):
        """
        Get repo to visit
        """
        logger.setLevel(self.get_verbosity(**options))
        repo = options.get("repo")
        if not repo:
            self.stderr.write("repo required")
            sys.exit(-1)
        repo = str(repo).lower()
        if worker_func := WORKER_FUNCS.get(repo):
            for purl, purls in worker_func():
                # check out repo
                repo = clone_repository(
                    repo_url="",
                    logger=logger,
                )
                # save purls to yaml
                ppath = hashid.get_package_purls_yml_file_path(purl)
                write_file(
                    base_path=repo.working_dir,
                    file_path=ppath,
                    data=purls,
                )
                # commit and push
                commit_and_push_changes(
                    repo=repo,
                    file_to_commit=ppath,
                    purl=purl,
                    logger=logger,
                )

        else:
            self.stderr.write(f"no function available for '{repo}'")
            sys.exit(-1)


def clone_repository(repo_url, logger=None):
    """Clone repository to local_path."""
    local_dir = tempfile.mkdtemp()

    authenticated_repo_url = repo_url.replace(
        "https://",
        f"https://{settings.FEDERATEDCODE_GIT_SERVICE_TOKEN}@",
    )
    repo = Repo.clone_from(url=authenticated_repo_url, to_path=local_dir, depth=1)

    repo.config_writer(config_level="repository").set_value(
        "user", "name", settings.FEDERATEDCODE_GIT_SERVICE_NAME
    ).release()

    repo.config_writer(config_level="repository").set_value(
        "user", "email", settings.FEDERATEDCODE_GIT_SERVICE_EMAIL
    ).release()

    return repo


def commit_and_push_changes(repo, file_to_commit, purl, remote_name="origin", logger=None):
    """Commit and push changes to remote repository."""
    author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
    author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL

    change_type = "Add" if file_to_commit in repo.untracked_files else "Update"
    commit_message = f"""\
    {change_type} scan result for {purl}

    Tool: pkg:github/aboutcode-org/purldb
    Reference: https://{settings.ALLOWED_HOSTS[0]}/

    Signed-off-by: {author_name} <{author_email}>
    """

    default_branch = repo.active_branch.name

    repo.index.add([file_to_commit])
    repo.index.commit(textwrap.dedent(commit_message))
    repo.git.push(remote_name, default_branch, "--no-verify")


def delete_local_clone(repo):
    """Remove local clone."""
    shutil.rmtree(repo.working_dir)


def write_file(base_path, file_path, data):
    """
    Write the ``data`` as YAML to the ``file_path`` in the ``base_path`` root directory.
    Create directories in the path as needed.
    """
    write_to = base_path / file_path
    write_to.parent.mkdir(parents=True, exist_ok=True)
    with open(write_to, encoding="utf-8", mode="w") as f:
        f.write(saneyaml.dump(data))
