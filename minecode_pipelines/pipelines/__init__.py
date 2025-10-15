#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


import shutil
from collections.abc import Iterable
import logging
from minecode_pipelines import pipes
from minecode_pipelines.pipes import write_packageurls_to_file

from aboutcode.hashid import get_package_base_dir
from aboutcode.pipeline import LoopProgress
from scanpipe.pipelines import Pipeline
from scanpipe.pipes import federatedcode

module_logger = logging.getLogger(__name__)


class MineCodeBasePipeline(Pipeline):
    """
    Base pipeline for mining PackageURLs.

    Uses:
        Subclass this Pipeline and implement ``mine_packageurls`` and ``packages_count``
        method. Also override the ``steps`` and ``commit_message`` as needed.
    """

    download_inputs = False

    @classmethod
    def steps(cls):
        return (
            cls.check_federatedcode_eligibility,
            cls.create_federatedcode_working_dir,
            # Add step(s) for downloading/cloning resource as required.
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

    def mine_and_publish_packageurls(self):
        """Mine and publish PackageURLs."""
        checked_out_repos = {}
        batch_size = 4000
        total_file_processed_count = 0
        total_commit_count = 0
        package_count = self.packages_count()
        progress = LoopProgress(
            total_iterations=package_count,
            logger=self.log,
            progress_step=1,
        )

        self.log(f"Mine PackageURL for {package_count:,d} packages.")
        for base, purls in progress.iter(self.mine_packageurls()):
            package_base_dir = get_package_base_dir(purl=base)

            package_root_dir = package_base_dir.parts[0]
            package_group = pipes.get_package_destination_repo(package_root_dir)

            if package_group not in checked_out_repos:
                checked_out_repos[package_group] = pipes.init_local_checkout(
                    repo_name=package_group,
                    working_path=self.working_path,
                    logger=self.log,
                )

            checkout = checked_out_repos[package_group]

            purl_file = write_packageurls_to_file(
                repo=checkout["repo"],
                base_dir=package_base_dir,
                packageurls=sorted(purls),
            )
            checkout["file_to_commit"].append(purl_file)
            checkout["file_processed_count"] += 1

            if len(checkout["file_to_commit"]) > batch_size:
                pipes.commit_and_push_checkout(
                    local_checkout=checkout,
                    commit_message=self.commit_message(checkout["commit_count"] + 1),
                    logger=self.log,
                )

        for checkout in checked_out_repos.values():
            final_commit_count = checkout["commit_count"] + 1
            pipes.commit_and_push_checkout(
                local_checkout=checkout,
                commit_message=self.commit_message(
                    commit_count=final_commit_count,
                    total_commit_count=final_commit_count,
                ),
                logger=self.log,
            )
            total_commit_count += checkout["commit_count"]
            total_file_processed_count += checkout["file_processed_count"]

        self.log(f"Processed PackageURL for {total_file_processed_count:,d} NuGet packages.")
        self.log(
            f"Pushed new PackageURL in {total_commit_count:,d} commits in {len(checked_out_repos):,d} repos."
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
            Reference: https://{settings.ALLOWED_HOSTS[0]}

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
        self.append_to_log(message)
        print(message)
