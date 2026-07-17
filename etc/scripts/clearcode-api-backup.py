#!/usr/bin/env python
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
"""
Script example to backup clearcode data using the clearcode API.

Pre-requisite:
 - A local installation of Python
 - The Python "requests" library, installed with "pip install requests".

 Run the backup script with:
    python clearcode-api-backup.py YYYY-MM-DD

 A directory "clearcode_backup_<timestamp>" will be created in the same directory
 that contains this script, and running this script will create one JSON backup
 file.
"""

import argparse
import json
import os
import logging
import sys
from collections import defaultdict
from datetime import datetime
from os.path import abspath, dirname, exists, join

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print(
        'The "requests" library is required by this script.\n'
        'Install it with: "pip install requests"'
    )
    sys.exit(1)

logging.captureWarnings(True)


class ProgressBar:
    progress_width = 75

    def __init__(self, output, total_count):
        self.output = output
        self.total_count = total_count
        self.prev_done = 0

    def update(self, count):
        if not self.output:
            return
        perc = count * 100 // self.total_count
        done = perc * self.progress_width // 100
        if self.prev_done >= done:
            return
        self.prev_done = done
        cr = "" if self.total_count == 1 else "\r"
        self.output.write(cr + "[" + "." * done + " " * (self.progress_width - done) + "]")
        if done == self.progress_width:
            self.output.write("\n")
        self.output.flush()


def get_all_objects_from_endpoint(url, extra_payload=None, verbose=True):
    """
    Return a list of all objects by calling the clearcode API endpoint `url`
    with the provided request. Paginate as needed.
    """
    objects = []
    payload = {}
    if extra_payload:
        payload.update(extra_payload)

    output = sys.stdout
    count_done = 0
    progress_bar = None

    next_url = f"{url}?{urlencode(payload)}"
    while next_url:
        response = requests.get(next_url)
        if response.status_code == requests.codes.ok:
            response_json = response.json()
            if verbose and not progress_bar:
                total_count = response_json.get("count")
                if not total_count:
                    return []
                print(f"{total_count} total")
                progress_bar = ProgressBar(output, total_count)
            results = response_json.get("results")
            objects.extend(results)
            if verbose:
                count_done += len(results)
                progress_bar.update(count_done)
            next_url = response_json.get("next")
        else:
            print("Error. Please restart the script.")
            sys.exit(1)

    return objects


def run_api_backup(api_root_url, extra_payload=None):
    """
    Execute a backup of clearcode data objects to JSON files.
    Given:
     - an `api_root_url` clearcode API root URL and
    this function:
     - creates a new backup directory named "clearcode_backup_<timestamp>"
       side-by-side with this script
     - calls the clearcode API to collect the list of all objects for each
       API endpoint
     - writes JSON files named after each endpoint with these collected
       objects in the backup directory
    On errors, this function will exit Python with a return code of 1.
    """
    endpoints = [
        "cditems",
    ]

    # Ensure all those dependencies are available in the backup file to feed the copy script.
    # Not needed when --last_modified_date is not provided since all the objects
    # for each endpoint will be collected.
    results = defaultdict(list)

    for endpoint_name in endpoints:
        endpoint_url = f"{api_root_url}{endpoint_name}/"

        print(f"Collecting {endpoint_name}...")
        objects = get_all_objects_from_endpoint(endpoint_url, extra_payload=extra_payload)
        print(f"{len(objects)} {endpoint_name} collected.")

        results[endpoint_name] += objects

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = join(abspath(dirname(__file__)), f"clearcode_backup_{timestamp}")
    if not exists(backup_dir):
        os.mkdir(backup_dir)

    for endpoint_name, objects in results.items():
        backup_file = join(backup_dir, f"{endpoint_name}.json")
        assert not exists(backup_file)
        with open(backup_file, "w") as f:
            f.write(json.dumps(objects, indent=2))

    print(f"Backup location: {backup_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="clearcode data backup using the clearcode API",
    )
    parser.add_argument(
        "--api-root-url",
        help="clearcode API endpoints root URL.",
        default="http://127.0.0.1:8000/api/",
    )
    parser.add_argument(
        "--last-modified-date",
        help='Limit the backup to object created/modified after that date. Format: "YYYY-MM-DD"',
        required=True,
    )
    args = parser.parse_args()

    extra_payload = {}
    try:
        datetime.strptime(args.last_modified_date, "%Y-%m-%d")
    except ValueError:
        print("Incorrect last_modified_date format. Expected YYYY-MM-DD")
        sys.exit(1)
    extra_payload["last_modified_date"] = args.last_modified_date

    print(f"Starting backup from {args.api_root_url}")
    run_api_backup(args.api_root_url, extra_payload)
    print("Backup completed.")
    sys.exit(0)
