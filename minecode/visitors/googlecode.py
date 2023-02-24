# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

from datetime import datetime
import os

from bs4 import BeautifulSoup

from packageurl import PackageURL

from minecode import seed
from minecode import visit_router
from minecode.utils import extract_file
from minecode.visitors import HttpJsonVisitor
from minecode.visitors import NonPersistentHttpVisitor
from minecode.visitors import HttpVisitor
from minecode.visitors import URI


class GooglecodeSeed(seed.Seeder):

    def get_seeds(self):
        yield 'https://code.google.com/archive/search?q=domain:code.google.com'
        yield 'https://storage.googleapis.com/google-code-archive/google-code-archive.txt.zip'


@visit_router.route('https://storage.googleapis.com/google-code-archive/google-code-archive.txt.zip')
class GooglecodeArchiveVisitor(NonPersistentHttpVisitor):
    """
    Fetch the googlecode archive file and extract it, and read the text file and get the URLs
    """

    def get_uris(self, content):
        """
        Return URIs by extracting and parsing the text file.

        Please refer to: https://github.com/pombredanne/swh-fetcher-googlecode

        For example, with Google
        Cloud Storage URL gs://google-code-archive/v2/code.google/hg4j/project.json,
        you can get the file's contents by URL-escaping the string and adding it to
        googleapis.com. e.g.
        https://www.googleapis.com/storage/v1/
        b/google-code-archive/o/v2%2Fcode.google.com%2Fhg4j%2Fproject.json?alt=media
        """
        extracted_location = extract_file(content)
        text_file = os.path.join(extracted_location, 'google-code-archive.txt')
        url_base = 'https://www.googleapis.com/storage/v1/b/{project_info}?alt=media'
        if os.path.exists(text_file):
            with open(text_file) as project_file:
                for project_line in project_file:
                    if not project_line:
                        continue
                    project_line = project_line.strip()
                    if project_line.startswith('gs://google-code-archive/v2') and project_line.endswith('/project.json'):
                        project_line = project_line.replace('gs://google-code-archive/v2', '')
                        package_name = project_line.replace('/project.json', '')
                        package_url = PackageURL(type='googlecode', name=package_name.strip('/')).to_string()
                        project_line = 'google-code-archive/o/v2' + project_line.replace('/', '%2F')
                        url = url_base.format(project_info=project_line)
                        yield URI(uri=url, package_url=package_url, source_uri=self.uri)


@visit_router.route('https://www.googleapis.com/storage/v1/b/google-code-archive/o/v2.*project.json\?alt=media')
class GoogleAPIProjectJsonVisitor(HttpJsonVisitor):
    """
    Fetch the json of the API URL and this will be used for mapper use.
    """
    pass


@visit_router.route('https://code.google.com/archive/search\?q=domain:code.google.com',
                    'https://code.google.com/archive/search\?q=domain:code.google.com&page=[0-9]*')
class GoogleProjectPagesVisitor(HttpVisitor):
    """
    Parse the passing google projects list pages, and return all project json url
    which the project belongs to in the current page, and the next page url.
    """

    def get_uris(self, content):
        """
        Return URIs for pagnitions of project lists
        """
        page = BeautifulSoup(content, 'lxml')
        projectjson_url_template = 'https://storage.googleapis.com/google-code-archive/v2/code.google.com/{project}/project.json'
        for page in page.find_all('a'):
            url = page['href']
            if url and 'https://code.google.com/archive/p/' in url:
                project_name = url.replace('https://code.google.com/archive/p/', '')
                project_api_url = projectjson_url_template.format(project=project_name)
                package_url = PackageURL(type='googlecode', name=project_name.strip('/')).to_string()
                yield URI(uri=project_api_url, package_url=package_url, source_uri=self.uri)
            if page.text.startswith('Next'):
                yield URI(uri=url, source_uri=self.uri)


@visit_router.route('https://storage.googleapis.com/google-code-archive/v2/code.google.com/.*/project.json')
class GoogleProjectJsonVisitor(HttpJsonVisitor):
    """
    Collect the project json for mapper use and also return the download page json url.
    """

    def get_uris(self, content):
        """
        Return the download json URL
        """
        yield URI(uri=self.uri.replace('project.json', 'downloads-page-1.json'))


@visit_router.route('https://storage.googleapis.com/google-code-archive/v2/code.google.com/.*/downloads-page-[0-9]*.json')
class GoogleDownloadsPageJsonVisitor(HttpJsonVisitor):
    """
    Collect download URIs and the next page related to the current download page.
    """

    def get_uris(self, content):
        """Yield the next download page based on current page number and total page number.
        and yield the download urls in the json, for example:
        https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/hg4j/hg4j_1.2m2.jar
        """
        url = self.uri
        page_num = content.get('pageNumber')
        total_pages = content.get('totalPages')
        name_template = 'downloads-page-{page}.json'
        filename = name_template.format(page=str(page_num))
        new_filename = name_template.format(page=str(page_num + 1))

        assert filename in url
        if page_num < total_pages:
            new_page_url = url.replace(filename, new_filename)
            yield URI(uri=new_page_url, source_uri=self.uri, )

        download_url_template = url.replace(filename, '') + '{file_name}'
        for download in content.get('downloads', []):
            file_name = download.get('filename')
            package_url = PackageURL(type='googlecode', name=file_name).to_string()
            if '_' in file_name and '.' in file_name:
                partitions = file_name.partition('_')
                package_name = partitions[0]
                version = partitions[-1].rpartition('.')[0]
                package_url = PackageURL(type='googlecode', name=package_name, version=version).to_string()
            download_url = download_url_template.format(file_name=file_name)
            last_modified_date = None
            release_date = download.get('releaseDate')
            if release_date:
                last_modified_date = datetime.fromtimestamp(release_date)
            yield URI(uri=download_url, package_url=package_url, file_name=file_name, source_uri=self.uri, date=last_modified_date, size=download.get('fileSize'), sha1=download.get('sha1Checksum'))
