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
import multiprocessing
import os
from pathlib import Path
import sys

from django.db.utils import IntegrityError

import click


"""
Load ClearlyDefined definitions and harvests from the filesystem

Operation
---------
This script walks a given `--input-dir` location and loads any ClearlyDefined data
into a Database (currently postgreSQL). 

Usage
-----
$ clearload --input-dir ~/path/to/ClearlyDefined/dir
"""


def walk_and_load_from_filesystem(input_dir, cd_root_dir):
    """
    Walk the given input_dir and load clearlydefined data into a Database.
    A CD item on the filesystem looks like the following:

    ~/clearly-local/npm/npmjs/@actions/github/revision/2.1.1.json.gz

    The resulting CDitem should be:

    CDitem.path = npm/npmjs/@actions/github/revision/2.1.1.json.gz
    CDitem.content = 'the file: 2.1.1.json.gz in bytes'
    """
    from clearcode import dbconf
    dbconf.configure()

    # for now, we count dirs too
    file_counter = 1
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            # output some progress
            print('                                        ', end='\r')
            print("Processing file #{}".format(file_counter), end='\r')
            file_counter +=1

            # TODO: check if the location is actually a CD data item.
            full_gzip_path = os.path.join(root, filename)
            full_json_path = full_gzip_path.rstrip('.gz')
            
            # normalize the `path` value by removing the arbitrary parent directory
            cditem_rel_path = os.path.relpath(full_json_path, cd_root_dir)
            
            with open(full_gzip_path, mode='rb') as f:
                content = f.read()
            
            from clearcode import models
            # Save to DB
            try:
                cditem = models.CDitem.objects.create(path=cditem_rel_path, content=content)
            except IntegrityError:
                # skip if we already have it in the DB
                continue


@click.command()

@click.option('--input-dir',
    type=click.Path(), metavar='DIR',
    help='Load content from this input directory that contains a tree of gzip-compressed JSON CD files')

@click.option('--cd-root-dir',
    type=click.Path(), metavar='DIR',
    help='specify root directory that contains a tree of gzip-compressed JSON CD files')

@click.help_option('-h', '--help')

def cli(input_dir=None, cd_root_dir=None, *arg, **kwargs):
    """
    Handle ClearlyDefined gzipped JSON scans by walking a clearsync directory structure, 
    creating CDItem objects and loading them into a PostgreSQL database. 
    """
    if not input_dir:
        sys.exit('Please specify an input directory using the `--input-dir` option.')
    if not cd_root_dir:
        sys.exit('Please specify the cd-root-directory using the --cd-root-dir option.')

    # get proper DB setup

    walk_and_load_from_filesystem(input_dir, cd_root_dir)
    print('                                        ', end='\r')
    print("Loading complete")


if __name__ == '__main__':
    cli()
