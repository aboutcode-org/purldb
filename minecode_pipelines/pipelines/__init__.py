#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import logging
import shutil
from collections.abc import Callable
from collections.abc import Iterable
from pathlib import Path

from aboutcode.federated import DataCluster
from aboutcode.federated import DataFederation
from aboutcode.pipeline import LoopProgress
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode

from minecode_pipelines import pipes
from minecode_pipelines.pipes import write_packageurls_to_file

module_logger = logging.getLogger(__name__)


class MineCodeBasePipeline(Pipeline):
    """
    Base pipeline for mining PackageURLs.

    Uses:
        Subclass this Pipeline and implement ``mine_packageurls`` and ``packages_count``
        method. Also override the ``steps`` and ``commit_message`` as needed.
    """

    download_inputs = False

    # Control wether to ovewrite or append mined purls to existing `purls.yml` file
    append_purls = False

    checked_out_repos = {}

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            # Add step(s) for downloading/cloning resource as required.
            cls.fetch_federation_config,
            cls.mine_and_publish_packageurls,
            cls.delete_working_dir,
        )

    def mine_packageurls(self) -> Iterable[tuple[str, list[str]]]:
        """
        Yield (base_purl, package_urls_list) tuples,

        where `base_purl` is a versionless PURL string,
        and `package_urls_list` is a list of versioned PURL strings.
        """
        raise NotImplementedError

    def packages_count(self) -> int:
        """
        Return the estimated number of packages for which PackageURLs are to be mined.

        Used by ``mine_and_publish_packageurls`` to log the progress of PackageURL mining.
        Note: If estimating package count is not feasable return `None`
        """
        raise NotImplementedError

    def check_federatedcode_eligibility(self):
        """
        Check if the project fulfills the following criteria for
        pushing the project result to FederatedCode.
        """
        federatedcode.check_federatedcode_configured_and_available()

    def create_federatedcode_working_dir(self):
        """Create temporary working dir."""
        self.working_path = federatedcode.create_federatedcode_working_dir()

    def fetch_federation_config(self):
        """Fetch config for PackageURL Federation."""
        data_federation = DataFederation.from_url(
            name="aboutcode-data",
            remote_root_url="https://github.com/aboutcode-data",
        )
        self.data_cluster = data_federation.get_cluster("purls")

    def mine_and_publish_packageurls(self):
        """Mine and publish PackageURLs."""

        _mine_and_publish_packageurls(
            packageurls=self.mine_packageurls(),
            total_package_count=self.packages_count(),
            data_cluster=self.data_cluster,
            checked_out_repos=self.checked_out_repos,
            working_path=self.working_path,
            append_purls=self.append_purls,
            commit_msg_func=self.commit_message,
            logger=self.log,
        )

    def delete_working_dir(self):
        """Remove temporary working dir."""
        shutil.rmtree(self.working_path)

    def commit_message(self, commit_count, total_commit_count="many"):
        """Return default commit message for pushing mined PackageURLs."""
        from django.conf import settings
        from scancodeio import VERSION

        author_name = settings.FEDERATEDCODE_GIT_SERVICE_NAME
        author_email = settings.FEDERATEDCODE_GIT_SERVICE_EMAIL

        tool_name = "pkg:github/aboutcode-org/scancode.io"

        return f"""\
            Add newly mined PackageURLs ({commit_count}/{total_commit_count})

            Tool: {tool_name}@v{VERSION}

            Signed-off-by: {author_name} <{author_email}>
            """

    def log(self, message, level=logging.INFO):
        """Log the given `message` to the current module logger and execution_log."""
        from datetime import datetime
        from datetime import timezone

        now_local = datetime.now(timezone.utc).astimezone()
        timestamp = now_local.strftime("%Y-%m-%d %T.%f %Z")
        message = f"{timestamp} {message}"
        module_logger.log(level, message)
        print(message)
        message = message.replace("\r", "\\r").replace("\n", "\\n")
        self.append_to_log(message)


def _mine_and_publish_packageurls(
    packageurls: Iterable,
    total_package_count: int,
    data_cluster: DataCluster,
    checked_out_repos: dict,
    working_path: Path,
    append_purls: bool,
    commit_msg_func: Callable,
    logger: Callable,
    batch_size: int = 4000,
):
    """Mine and publish PackageURLs."""
    total_file_processed_count = 0
    total_commit_count = 0
    iterator = packageurls

    if total_package_count:
        progress = LoopProgress(
            total_iterations=total_package_count,
            logger=logger,
            progress_step=1,
        )
        iterator = progress.iter(iterator)
        logger(f"Mine PackageURL for {total_package_count:,d} packages.")

    for base, purls in iterator:
        if not purls or not base:
            continue

        package_repo, datafile_path = data_cluster.get_datafile_repo_and_path(purl=base)
        if package_repo not in checked_out_repos:
            checked_out_repos[package_repo] = pipes.init_local_checkout(
                repo_name=package_repo,
                working_path=working_path,
                logger=logger,
            )

        checkout = checked_out_repos[package_repo]
        purl_file = write_packageurls_to_file(
            repo=checkout["repo"],
            relative_datafile_path=datafile_path,
            packageurls=sorted(purls),
            append=append_purls,
        )
        checkout["file_to_commit"].append(purl_file)
        checkout["file_processed_count"] += 1

        if len(checkout["file_to_commit"]) > batch_size:
            pipes.commit_and_push_checkout(
                local_checkout=checkout,
                commit_message=commit_msg_func(checkout["commit_count"] + 1),
                logger=logger,
            )

    for checkout in checked_out_repos.values():
        final_commit_count = checkout["commit_count"] + 1
        pipes.commit_and_push_checkout(
            local_checkout=checkout,
            commit_message=commit_msg_func(
                commit_count=final_commit_count,
                total_commit_count=final_commit_count,
            ),
            logger=logger,
        )
        total_commit_count += checkout["commit_count"]
        total_file_processed_count += checkout["file_processed_count"]

    logger(f"Processed PackageURL for {total_file_processed_count:,d} packages.")
    logger(
        f"Pushed new PackageURL in {total_commit_count:,d} commits in {len(checked_out_repos):,d} repos."
    )
