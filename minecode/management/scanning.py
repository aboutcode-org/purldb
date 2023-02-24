#
# Copyright (c) 2018 by nexB, Inc. http://www.nexb.com/ - All rights reserved.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import sys
import time

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

# TODO: Simplify this: this is 'user:pass' atm
# TODO: Look at DejaCode toolkit for auth
SCANCODEIO_AUTH = tuple(get_settings('SCANCODEIO_AUTH').split(':'))

SCANCODEIO_API_URL_SCANS = '{}/scans/'.format(SCANCODEIO_URL) if SCANCODEIO_URL else None


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
    # the actual URI being scanned:
    # "uri": "https://repo1.maven.org/maven2/io/github/subiyacryolite/jds/3.0.1/jds-3.0.1-sources.jar",
    uri = attr.ib(default=None)
    # sha1 of URI being scanned:
    # "sha1": "9165ed2d6033039b9a2e1f4a67b512b7b7347155",
    sha1 = attr.ib(default=None)
    # md5 of URI being scanned:
    # "md5": "bb19d01dfc9715944638e92e22489fd1",
    md5 = attr.ib(default=None)
    # size of URI being scanned:
    # "size": "74150",
    size = attr.ib(default=None)
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
    # actual full scan details API URL
    # "data_url": "https://scancode.io/api/scans/ac85c2f0-09b9-4ca1-b0e4-91523a636ccf/data/",
    data_url = attr.ib(default=None)
    # scan summary API URL
    # "summary_url": "https://scancode.io/api/scans/ac85c2f0-09b9-4ca1-b0e4-91523a636ccf/summary/"
    summary_url = attr.ib(default=None)

    @classmethod
    def from_response(self, url, uuid, uri, sha1, md5, size, created_date,
                      task_start_date, task_end_date, task_exitcode,
                      status, execution_time, data_url, summary_url,
                      **kwargs):
        """
        Return a Scan object built from an API response data arguments.
        """
        return Scan(
            url=url, uuid=uuid, uri=uri, sha1=sha1, md5=md5, size=size,
            created_date=created_date, task_start_date=task_start_date,
            task_end_date=task_end_date, task_exitcode=task_exitcode,
            status=status, data_url=data_url, summary_url=summary_url,
            execution_time=execution_time
        )

    @property
    def pending(self):
        return self.status == 'not started yet'

    @property
    def in_progress(self):
        return self.status == 'in progress'

    @property
    def completed(self):
        return self.status == 'completed'

    @property
    def failed(self):
        return self.status == 'failed'


def query_scans(uri, api_url=SCANCODEIO_API_URL_SCANS, api_auth=SCANCODEIO_AUTH):
    """
    Return scan information for `uri` if `uri` has already been scanned by ScanCode.io
    """
    payload = {'uri': uri}
    response = requests.get(url=api_url, params=payload, auth=api_auth)
    if not response.ok:
        response.raise_for_status()
    results = response.json()['results']
    if results and len(results) == 1:
        return results[0]


def submit_scan(uri, email=None,
                api_url=SCANCODEIO_API_URL_SCANS, api_auth=SCANCODEIO_AUTH):
    """
    Submit a scan request for `uri` to ScanCode.io and return a Scan object on
    success. Raise an exception on error.
    """
    logger.debug('submit_scan: uri', uri, 'api_url:', api_url, 'api_auth:', api_auth)
    request_args = {'uri': uri, 'timeout': REQUEST_TIMEOUT}
    if email:
        request_args['email'] = email

    response = requests.post(url=api_url, json=request_args, auth=api_auth)
    if not response.ok:
        if response.status_code == requests.codes.bad_request:
            if 'scan with this URI already exists.' in response.json()['uri']:
                query_results = query_scans(uri, api_url=api_url, api_auth=api_auth)
                if query_results:
                    scan = Scan.from_response(**query_results)
        else:
            response.raise_for_status()
    else:
        scan = Scan.from_response(**response.json())
        uuid = scan.uuid
        if not uuid:
            msg = 'Failed to to submit scan UUID for URI: "{uri}".\n'.format(**locals())
            msg += repr(response.json())
            raise Exception(msg)
    return scan


def get_scan_url(scan_uuid, api_url=SCANCODEIO_API_URL_SCANS, suffix=''):
    """
    Return a scancode.io scan API URL built from the Scan UUID `scan_uuid` or
    None. Return the basic URL to get scan request information. Optionally adds
    a `suffix` (such as /data or /summary) to get scans data.

    For example:
        https://scancode.io/api/scans/b15f2dcb-46ef-43e1-b5e3-563871ce59cc/
    """

    # FIXME: Why would scan_uuid be empty?
    if scan_uuid:
        base_url = api_url and api_url.rstrip('/') or ''
        url = '{base_url}/{scan_uuid}/{suffix}'.format(**locals())
        # scancode.io seems to demand a trailing slash
        url = url.rstrip('/')
        url = url + '/'
        return url


def _call_scan_get_api(scan_uuid, endpoint='',
                       api_url=SCANCODEIO_API_URL_SCANS, api_auth=SCANCODEIO_AUTH):
    """
    Send a get request to the scan API for `scan_uuid` and return response
    mapping from a JSON response. Call either the plain scan enpoint or the data
    or summary endpoints based on the value of the `endpoint `arg. Raise an
    exception on error.
    """
    scan_url = get_scan_url(scan_uuid, api_url=api_url, suffix=endpoint)
    response = requests.get(url=scan_url, timeout=REQUEST_TIMEOUT, auth=api_auth)
    if not response.ok:
        response.raise_for_status()
    return response.json()


def get_scan_info(scan_uuid, api_url=SCANCODEIO_API_URL_SCANS, api_auth=SCANCODEIO_AUTH):
    """
    Return a Scan object for `scan_uuid` fetched from ScanCode.io or None.
    Raise an exception on error.
    """
    results = _call_scan_get_api(scan_uuid, endpoint='', api_url=api_url, api_auth=api_auth)
    return Scan.from_response(**results)


def get_scan_summary(scan_uuid, api_url=SCANCODEIO_API_URL_SCANS, api_auth=SCANCODEIO_AUTH):
    """
    Return scan summary data as a mapping for a `scan_uuid` fetched from
    ScanCode.io or None. Raise an exception on error.
    """
    return _call_scan_get_api(scan_uuid, endpoint='summary', api_url=api_url, api_auth=api_auth)


def get_scan_data(scan_uuid, api_url=SCANCODEIO_API_URL_SCANS, api_auth=SCANCODEIO_AUTH):
    """
    Return scan details data as a mapping for a `scan_uuid` fetched from
    ScanCode.io or None. Raise an exception on error.
    """
    # FIXME: we should return a temp location instead
    return _call_scan_get_api(scan_uuid, endpoint='data', api_url=api_url, api_auth=api_auth)


class ScanningCommand(VerboseCommand):
    """
    Base command class for processing ScannableURIs.
    """
    # subclasses must override
    logger = None

    api_url = SCANCODEIO_API_URL_SCANS

    api_auth = SCANCODEIO_AUTH

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
