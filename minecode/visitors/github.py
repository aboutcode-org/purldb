# -*- coding: utf-8 -*-
#
# Copyright (c) nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from datetime import date
from datetime import datetime
import json
import logging

from github.MainClass import Github
from github.Repository import Repository
from github.Download import Download
from packageurl import PackageURL

from minecode import visit_router, seed
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import URI


logger = logging.getLogger(__name__)

TRACE = False
if TRACE:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class GithubSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://api.github.com/repositories?since=0'


@visit_router.route('https://api.github.com/repositories\?since=\d+')
class GithubReposVisitor(HttpJsonVisitor):
    """
    Visitor to run repositories request to get all repositories by increasing since symbol 100 each loop time.
    Refer to: https://developer.github.com/v3/repos/#list-all-public-repositories
              https://api.github.com/repositories
    """
    def get_uris(self, content):
        repo_request_base = 'https://api.github.com/repositories?since='
        has_content = False
        if content:
            for entry in content:
                has_content = True
                url = entry.get('url')
                # Take full_name instead of name here since we want to keep more info, especially when forming the package url
                #     "name": "grit",
                #     "full_name": "mojombo/grit",
                name = entry.get('full_name')
                if url:
                    package_url = None
                    if name:
                        package_url = PackageURL(type='github', name=name).to_string()
                    # Yield URI for GithubSingleRepoVisitor use
                    yield URI(uri=url, package_url=package_url, source_uri=self.uri)
        if not has_content:
            logger.info('The content of the response is empty, the processing might be finished for URI: {}'.format(self.uri))
        else:
            uri = self.uri
            current_id = uri.replace('https://api.github.com/repositories?since=', '')
            current_id = int(current_id)
            # 100 is fixed since each page has 100 entries. Plus 100 means to go from next page.
            new_id = current_id + 100
            new_url = repo_request_base + str(new_id)
            yield URI(uri=new_url, source_uri=self.uri)


@visit_router.route('https://api.github.com/repos/[\w\-\.]+/[\w\-\.]+')
class GithubSingleRepoVisitor(HttpJsonVisitor):
    """
    Visitor to get the json and add more content with GitHub API from one repo.
    For example: https://api.github.com/repos/mojombo/grit
    """

    def fetch(self, uri, timeout=None):
        """
        Having its own fetch function instead of inheriting from HttpJsonVisitor class is because:
        The json itself has lots of URL info, the Github API can get content without acccessing the URLs inside the json explicitly.
        The main idea is to fetch download_url...
        """
        full_name = uri.replace('https://api.github.com/repos/', '')
        g = Github()
        repo = g.get_repo(full_name)

        common_data = OrderedDict(
            name=repo.name,
            description=repo.description,
            blobs_url=repo.blobs_url,
            language=repo.language,
            size=repo.size,
            homepage=repo.homepage,
            html_url=repo.html_url,
            etag=repo.etag,
            full_name=repo.full_name,
            repo_id=repo.id,
            ssh_url=repo.ssh_url,
            source_url=repo.svn_url,
            clone_url=repo.clone_url,
            watchers_count=repo.watchers,
            master_branch=repo.master_branch,
            updated_at=json_serial_date_obj(repo.updated_at),
            pushed_at=json_serial_date_obj(repo.pushed_at),
        )

        if repo.owner:
            common_data['owner'] = repo.owner.name
        if repo._issues_url:
            common_data['issue_url'] = repo._issues_url.value

        if repo._git_url:
            common_data['git_url'] = repo._git_url.value

        if repo.organization:
            repo.origanization = repo.organization.name

        downloads = []
        if repo.get_downloads():
            for download in list(repo.get_downloads()):
                downloads.append(OrderedDict(
                    name=download.name,
                    url=download.url,
                    size=download.size,
                    s3_url=download.s3_url,
                    created_at=json_serial_date_obj(download.created_at),
                    download_count=download.download_count,
                    description=download.description,
                    redirect=download.redirect,
                    signature=download.signature,
                    html_url=download.html_url,
                    bucket=download.bucket,
                    acl=download.acl,
                    accesskeyid=download.accesskeyid,
                    expirationdate=json_serial_date_obj(download.expirationdate),
                ))
        common_data['downloads'] = downloads

        tags = []
        if repo.get_tags():
            for tag in list(repo.get_tags()):
                tag_info = OrderedDict(
                    name=tag.name,
                    tarball_url=tag.tarball_url,
                    zipball_url=tag.zipball_url,
                )
                if tag.commit:
                    tag_info['sha1'] = tag.commit.sha
                tags.append(tag_info)
        common_data['tags'] = tags

        if not common_data.get('tags') and not common_data.get('downloads'):
            # If there is no downloads and tags, let's make the download_url by forming archive/master.zip at the end
            # For example, the base html is: https://github.com/collectiveidea/calendar_builder
            # The final download_url is https://github.com/collectiveidea/calendar_builder/archive/master.zip
            branches_download_urls = []
            download_url_bases = '{html_url}/archive/{branch_name}.zip'
            if repo.get_branches():
                for branch in list(repo.get_branches()):
                    branches_download_urls.append(download_url_bases.format(html_url=common_data.get('html_url'), branch_name=branch.name))
            common_data['branches_download_urls'] = branches_download_urls

        common_data['labels'] = []
        if repo.get_labels():
            for label in repo.get_labels():
                common_data['labels'].append(label.name)

        return json.dumps(common_data)


def json_serial_date_obj(obj):
    """JSON serializer for date object"""
    if obj and isinstance(obj, (datetime, date)):
        return obj.isoformat()
