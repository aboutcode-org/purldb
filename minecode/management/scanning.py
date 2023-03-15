#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import hashlib
import logging
import sys
import time
import json

import attr
import requests

from minecode.management.commands import VerboseCommand
from minecode.management.commands import get_settings

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

# sleep duration in seconds when the queue is empty
SLEEP_WHEN_EMPTY = 1

# in seconds
REQUEST_TIMEOUT = 10

SCANCODEIO_URL = get_settings('SCANCODEIO_URL').rstrip('/')

SCANCODEIO_API_KEY = get_settings('SCANCODEIO_API_KEY')
SCANCODEIO_AUTH_HEADERS = {
    'Authorization': f'Token {SCANCODEIO_API_KEY}'
} if SCANCODEIO_API_KEY else {}

SCANCODEIO_API_URL_PROJECTS = f'{SCANCODEIO_URL}/projects/' if SCANCODEIO_URL else None


@attr.attrs(slots=True)
class Scan(object):
    """
    Represent a scan record as returned by the ScanCode.io API /scans/<UUID>
    endpoint.
    """
    # this is the API endpoint full URL:
    # "url": "https://scancode.io/api/scans/ac85c2f0-09b9-4ca1-b0e4-91523a636ccf/",
    url = attr.ib(default=None)
    # this is the UUDI for for scan:
    # "uuid": "ac85c2f0-09b9-4ca1-b0e4-91523a636ccf",
    uuid = attr.ib(default=None)
    # The UUID for the scan run
    run_uuid = attr.ib(default=None)
    # the actual URI being scanned:
    # "uri": "https://repo1.maven.org/maven2/io/github/subiyacryolite/jds/3.0.1/jds-3.0.1-sources.jar",
    uri = attr.ib(default=None)
    # set at creation of a scan request
    # "created_date": "2018-06-19T08:33:34.953429Z",
    created_date = attr.ib(default=None)
    # set at start of the actual fetch+scan:
    # "task_start_date": null,
    task_start_date = attr.ib(default=None)
    # set at end of scanning:
    # "task_end_date": null,
    task_end_date = attr.ib(default=None)
    # null and then 0 on success or 1 or else on failure
    task_exitcode = attr.ib(default=None)
    # ignore for now
    # task_output=attr.ib(default=None)
    # "status": 'not started yet', 'failed', 'in progress', 'completed'
    status = attr.ib(default=None)
    # as a time stamp
    execution_time = attr.ib(default=None)

    @classmethod
    def from_response(cls, url, uuid, runs, input_sources, **kwargs):
        """
        Return a Scan object built from an API response data arguments.
        """
        run_data = {}
        if len(runs) > 0:
            run_data = runs[0]

        run_uuid = run_data.get("uuid")
        created_date = run_data.get("created_date")
        task_start_date = run_data.get("task_start_date")
        task_end_date = run_data.get("task_end_date")
        task_exitcode = run_data.get("task_exitcode")
        status = run_data.get("status")
        execution_time = run_data.get('execution_time')

        if len(input_sources) > 0:
            uri = input_sources[0]["source"]

        return Scan(
            url=url, uuid=uuid, run_uuid=run_uuid, uri=uri,
            created_date=created_date, task_start_date=task_start_date,
            task_end_date=task_end_date, task_exitcode=task_exitcode,
            status=status, execution_time=execution_time
        )

    @property
    def results_url(self):
        url = self.url.rstrip('/')
        return f'{url}/results/'

    @property
    def not_started(self):
        return self.status == 'not_started'

    @property
    def queued(self):
        return self.status == 'queued'

    @property
    def running(self):
        return self.status == 'running'

    @property
    def success(self):
        return self.status == 'success'

    @property
    def failure(self):
        return self.status == 'failure'

    @property
    def stopped(self):
        return self.status == 'stopped'

    @property
    def stale(self):
        return self.status == 'stale'


def uri_fingerprint(uri):
    """
    Return the SHA1 hex digest of `uri`
    """
    encoded_uri = uri.encode('utf-8')
    return hashlib.sha1(encoded_uri).hexdigest()


def query_scans(uri, api_url=SCANCODEIO_API_URL_PROJECTS, api_auth_headers=SCANCODEIO_AUTH_HEADERS, response_save_loc=''):
    """
    Return scan information for `uri` if `uri` has already been scanned by ScanCode.io
    """
    payload = {'name': uri_fingerprint(uri)}
    response = requests.get(url=api_url, params=payload, headers=api_auth_headers)
    response_json = response.json()
    if response_save_loc:
        with open(response_save_loc, 'w') as f:
            json.dump(response_json, f)
    if not response.ok:
        response.raise_for_status()
    results = response_json['results']
    if results and len(results) == 1:
        return results[0]


def submit_scan(
    uri,
    api_url=SCANCODEIO_API_URL_PROJECTS,
    api_auth_headers=SCANCODEIO_AUTH_HEADERS,
    response_save_loc=''
):
    """
    Submit a scan request for `uri` to ScanCode.io and return a Scan object on
    success. Raise an exception on error.
    """
    logger.debug('submit_scan: uri', uri, 'api_url:', api_url, 'api_auth_headers:', api_auth_headers)
    request_args = {
        'name': uri_fingerprint(uri),
        'pipeline': 'scan_and_fingerprint_codebase',
        'input_urls': [
            uri
        ],
        'execute_now': True
    }

    response = requests.post(url=api_url, data=request_args, headers=api_auth_headers)
    response_json = response.json()
    if response_save_loc:
        with open(response_save_loc, 'w') as f:
            json.dump(response_json, f)

    if not response.ok:
        if response.status_code == requests.codes.bad_request:
            name = response_json.get('name')
            if name and 'project with this name already exists.' in name:
                query_results = query_scans(uri, api_url=api_url, api_auth_headers=api_auth_headers)
                if query_results:
                    scan = Scan.from_response(**query_results)
            else:
                response.raise_for_status()
    else:
        scan = Scan.from_response(**response_json)
        uuid = scan.uuid
        if not uuid:
            msg = 'Failed to to submit scan UUID for URI: "{uri}".\n'.format(**locals())
            msg += repr(response_json)
            raise Exception(msg)
    return scan


def get_scan_url(scan_uuid, api_url=SCANCODEIO_API_URL_PROJECTS, suffix=''):
    """
    Return a scancode.io scan API URL built from the Scan UUID `scan_uuid` or
    None. Return the basic URL to get scan request information. Optionally adds
    a `suffix` (such as /data or /summary) to get scans data.

    For example:
        https://scancode.io/api/projects/b15f2dcb-46ef-43e1-b5e3-563871ce59cc/
    """

    base_url = api_url and api_url.rstrip('/') or ''
    url = f'{base_url}/{scan_uuid}/{suffix}'
    # scancode.io seems to demand a trailing slash
    url = url.rstrip('/')
    url = url + '/'
    return url


def _call_scan_get_api(scan_uuid, endpoint='',
                       api_url=SCANCODEIO_API_URL_PROJECTS, api_auth_headers=SCANCODEIO_AUTH_HEADERS):
    """
    Send a get request to the scan API for `scan_uuid` and return response
    mapping from a JSON response. Call either the plain scan enpoint or the data
    or summary endpoints based on the value of the `endpoint `arg. Raise an
    exception on error.
    """
    scan_url = get_scan_url(scan_uuid, api_url=api_url, suffix=endpoint)
    response = requests.get(url=scan_url, timeout=REQUEST_TIMEOUT, headers=api_auth_headers)
    if not response.ok:
        response.raise_for_status()
    return response.json()


def get_scan_info(
    scan_uuid,
    api_url=SCANCODEIO_API_URL_PROJECTS,
    api_auth_headers=SCANCODEIO_AUTH_HEADERS,
    get_scan_info_save_loc=''
):
    """
    Return a Scan object for `scan_uuid` fetched from ScanCode.io or None.
    Raise an exception on error.
    """
    results = _call_scan_get_api(scan_uuid, endpoint='', api_url=api_url, api_auth_headers=api_auth_headers)
    if get_scan_info_save_loc:
        with open(get_scan_info_save_loc, 'w') as f:
            json.dump(results, f)
    return Scan.from_response(**results)


def get_scan_data(
    scan_uuid,
    api_url=SCANCODEIO_API_URL_PROJECTS,
    api_auth_headers=SCANCODEIO_AUTH_HEADERS,
    get_scan_data_save_loc=''
):
    """
    Return scan details data as a mapping for a `scan_uuid` fetched from
    ScanCode.io or None. Raise an exception on error.
    """
    # FIXME: we should return a temp location instead
    results = _call_scan_get_api(scan_uuid, endpoint='results', api_url=api_url, api_auth_headers=api_auth_headers)
    if get_scan_data_save_loc:
        with open(get_scan_data_save_loc, 'w') as f:
            json.dump(results, f)
    return results


class ScanningCommand(VerboseCommand):
    """
    Base command class for processing ScannableURIs.
    """
    # subclasses must override
    logger = None

    api_url = SCANCODEIO_API_URL_PROJECTS

    api_auth_headers = SCANCODEIO_AUTH_HEADERS

    def add_arguments(self, parser):
        parser.add_argument(
            '--exit-on-empty',
            dest='exit_on_empty',
            default=False,
            action='store_true',
            help='Do not loop forever. Exit when the queue is empty.')

        parser.add_argument(
            '--max-uris',
            dest='max_uris',
            default=0,
            action='store',
            help='Limit the number of Scannable URIs processed to a maximum number. '
                 '0 means no limit. Used only for testing.')

    def handle(self, *args, **options):
        exit_on_empty = options.get('exit_on_empty')
        max_uris = options.get('max_uris', 0)

        uris_counter = self.process_scans(
            exit_on_empty=exit_on_empty,
            max_uris=max_uris,
            # Pass options to allow subclasses to add their own options
            options=options
        )
        self.stdout.write('Processed {} ScannableURI.'.format(uris_counter))

    @classmethod
    def process_scans(cls, exit_on_empty=False, max_uris=0, **kwargs):
        """
        Run an infinite scan processing loop. Return a processed URis count.

        Get the next available candidate ScannableURI and request a scan from
        ScanCode.io. Loops forever and sleeps a short while if there are no
        ScannableURI left to scan.
        """
        uris_counter = 0
        sleeping = False

        while True:
            if cls.MUST_STOP:
                cls.logger.info('Graceful exit of the scan processing loop.')
                break

            if max_uris and uris_counter >= max_uris:
                cls.logger.info('max_uris requested reached: exiting scan processing loop.')
                break

            scannable_uri = cls.get_next_uri()

            if not scannable_uri:
                if exit_on_empty:
                    cls.logger.info('exit-on-empty requested: No more scannable URIs, exiting...')
                    break

                # Only log a single message when we go to sleep
                if not sleeping:
                    sleeping = True
                    cls.logger.info('No more scannable URIs, sleeping for at least {} seconds...'.format(SLEEP_WHEN_EMPTY))

                time.sleep(SLEEP_WHEN_EMPTY)
                continue

            cls.logger.info('Processing scannable URI: {}'.format(scannable_uri))

            cls.process_scan(scannable_uri, **kwargs)
            uris_counter += 1
            sleeping = False

        return uris_counter

    @classmethod
    def get_next_uri(self):
        """
        Return a locked ScannableURI for processing.
        Subclasses must implement

        Typically something like:
            with transaction.atomic():
                scannable_uri = ScannableURI.objects.get_next_scannable()
        """
        pass

    @classmethod
    def process_scan(scannable_uri, **kwargs):
        """
        Process a single `scannable_uri` ScannableURI. Subclasses must implement.
        If sucessfully processed the ScannableURI must be updated accordingly.
        """
        pass
