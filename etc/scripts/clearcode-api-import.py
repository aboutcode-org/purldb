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
Script to import clearcode data using the clearcode API.

Pre-requisite:
 - A local installation of Python
 - The Python "requests" library, installed with "pip install requests".
 - a clearcode backup directory, (output of running clearcode-api-backup.py)

After completion, the clearcode database will be updated with the items from the
clearcode backup
"""


import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from os.path import abspath
from os.path import dirname
from os.path import join

try:
    import requests
except ImportError:
    print(
        'The "requests" library is required by this script.\n'
        'Install it with: "pip install requests"'
    )
    sys.exit(1)

logging.captureWarnings(True)


def run_api_copy(api_root_url, backup_directory):
    headers = {
        "Content-type": "application/json",
    }

    endpoints = [
        "cditems",
    ]

    copy_results = {}
    for endpoint in endpoints:
        backup_file = os.path.join(backup_directory, f"{endpoint}.json")

        if not os.path.exists(backup_file):
            print(f"{endpoint.title()} backup file is not available, skipped.")
            continue

        with open(backup_file) as f:
            source_objects = json.load(f)

        api_endpoint_url = f"{api_root_url}{endpoint}/"
        if requests.get(api_endpoint_url, headers=headers).status_code != 200:
            print(f"{endpoint.title()} API endpoint not available.")
            continue

        print(f"Copying {len(source_objects)} {endpoint}...")
        endpoint_results = defaultdict(list)
        for i, data in enumerate(source_objects):
            if not (i % 10):
                print(".", end="", flush=True)
            object_api_url = "{}{}/".format(api_endpoint_url, data["uuid"])
            response = requests.get(object_api_url, headers=headers)
            object_exists = response.status_code == 200

            if object_exists:
                put_response = requests.put(
                    object_api_url, headers=headers, data=json.dumps(data)
                )
                if put_response.status_code == 200:  # Updated
                    endpoint_results["updated"].append(data)
                else:
                    print(
                        "Update error:",
                        put_response
                        and put_response.json()
                        or repr(put_response.content),
                    )
                    endpoint_results["update_errors"].append(
                        {"data": data, "error": put_response.json()}
                    )

            else:
                post_response = requests.post(
                    api_endpoint_url, headers=headers, data=json.dumps(data)
                )
                if post_response.status_code == 201:  # Created
                    endpoint_results["created"].append(data)
                else:
                    print("Create error:", post_response.json())
                    endpoint_results["create_errors"].append(
                        {"data": data, "error": post_response.json()}
                    )
        copy_results[endpoint] = endpoint_results
    return copy_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="clearcode data import using the clearcode API",
    )
    parser.add_argument(
        "--clearcode-target-api-url",
        help="clearcode target instance API endpoints root URL. http://hostname/api/",
        default="http://127.0.0.1:8000/api/",
    )
    parser.add_argument(
        "--backup-directory",
        help="Path of the backup directory created by clearcode-api-backup.py script",
        required=True,
    )
    args = parser.parse_args()

    if not args.clearcode_target_api_url:
        print(
            "A clearcode target instance API endpoints root URL is required.\n"
            "Provide one using the --clearcode-target-api-url argument."
        )
        sys.exit(1)

    backup_directory = args.backup_directory

    if not backup_directory.startswith("/"):
        cwd = os.getcwd()
        backup_directory = abspath(join(cwd, backup_directory))

    if not os.path.exists(backup_directory):
        print(f'Directory "{backup_directory}" does not exists.')
        sys.exit(1)

    print(
        f"Importing objects from {backup_directory} to {args.clearcode_target_api_url}"
    )
    copy_results = run_api_copy(args.clearcode_target_api_url, backup_directory)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = join(
        abspath(dirname(__file__)), f"copy_results_{timestamp}.json"
    )
    with open(output_file, "w") as f:
        f.write(json.dumps(copy_results, indent=2))
    print("Copy completed.")
    print(f"Results saved in {output_file}")
    sys.exit(0)
