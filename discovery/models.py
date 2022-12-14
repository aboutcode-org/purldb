#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#


from datetime import timedelta
import logging
import sys

from django.db import models
from django.utils import timezone


from discovery import map_router
from discovery import visit_router

# UnusedImport here!
# But importing the mappers and visitors module triggers routes registration
from discovery import mappers  # NOQA
from discovery import visitors  # NOQA

from packagedb.models import Package


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(logging.INFO)

# logger = logging.getLogger(__name__)
# handler = logging.StreamHandler()
# logger.addHandler(handler)


def get_canonical(uri):
    """
    Return the canonical representation of a URI such that logically identical
    URIs have the same canonical form even if they have small text differences.

    Based on the equiv() method from https://github.com/seomoz/url-py as their
    canonical() method is not doing enough for us.

    Note: when a default port corresponding to the scheme is explicitly declared
    in the URI it is removed from the canonical output.
    """
    import urlpy
    normalized = urlpy.parse(uri).canonical().defrag().sanitize().punycode()
    # Taken from an old version of urlpy (latest does not have the PORTS dict
    # See: https://github.com/seomoz/url-py/blob/1d0efdda102cc48ce9dbcc41154296cea1d28c1f/url.py#L46
    PORTS = {
        'http': 80,
        'https': 443
    }
    if normalized.port == PORTS.get(normalized.scheme, None):
        normalized.remove_default_port()
    return normalized.unicode


class BaseURI(models.Model):
    """
    A base abstract model to store URI for crawling, scanning and indexing.
    Also used as a processing "to do" queue for visiting and mapping these URIs.
    """
    uri = models.CharField(
        max_length=2048,
        db_index=True,
        help_text='URI for this resource. This is the unmodified original URI.',
    )

    canonical = models.CharField(
        max_length=3000,
        db_index=True,
        help_text='Canonical form of the URI for this resource that must be '
                  'unique across all ResourceURI.',
    )

    source_uri = models.CharField(
        max_length=2048,
        null=True,
        blank=True,
        help_text='Optional: real source remote URI for this visit.'
        'For example for a package repository index is a typical source '
        'via which a first level of package data is fetched. And it is '
        'not the URI in the uri field. It is just the source of the fetch'
        'Or the source may be a mirror URI used for fetching.'
    )

    priority = models.PositiveIntegerField(
        # Using default because NULL is ordered first on Postgres.
        default=0,
        db_index=True,
        help_text='Absolute procdssing priority of a URI (default to zero), '
                  'higher number means higher priority, zero means lowest '
                  'priority.',
    )

    wip_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Work In Progress. This is a timestamp set at the start of a '
                  'visit or mapping or indexing or null when no processing is '
                  'in progress.',
    )

    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='File name of a resource sometimes part of the URI proper '
                  'and sometimes only available through an HTTP header.',
    )

    # FIXME: 2147483647 is the max size which means we cannot store more than 2GB files
    size = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Size in bytes of the file represented by this ResourceURI.',
    )

    sha1 = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        help_text='SHA1 checksum hex-encoded (as in the sha1sum command) of the '
                  'content of the file represented by this ResourceURI.',
    )

    md5 = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text='MD5 checksum hex-encoded (as in the md5sum command) of the '
                  'content of the file represented by this ResourceURI.',
    )

    sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text='SHA256 checksum hex-encoded (as in the sha256sum command) of the '
                  'content of the file represented by this ResourceURI.',
    )

    last_modified_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Timestamp set to the last modified date of the remote '
                  'resource represented by this URI such as the modified date '
                  'of a file, the lastmod value on a sitemap or the modified '
                  'date returned by an HTTP resource.',
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.uri

    def normalize_fields(self, exclude=None):
        """
        Why do we normalize? In some weird cases wee may receive damaged
        data (e.g. a very long SHA1) and rather than push down the
        validation or fail an insert we can normalize the data in a
        single place.
        """
        # FIXME: we should use a custom field instead
        sha1 = self.sha1
        if sha1 and len(sha1) != 40:
            logger.warning(
                'ResourceURI.normalize_fields() for URI: "{}" - '
                'Invalid SHA1 length: "{}": SHA1 ignored!'
                .format(self.uri, sha1))
            self.sha1 = None


# TODO: Use the QuerySet.as_manager() for more flexibility and chaining.
class ResourceURIManager(models.Manager):

    def insert(self, uri, **extra_fields):
        """
        Create and return a new ResourceURI after computing its canonical URI
        representation.
        Return None if the insertion failed when an identical canonical entry
        already exist (as the canonical URI field is unique).
        """
        resource_uri, created = self.get_or_create(uri=uri, **extra_fields)
        if created:
            return resource_uri

    def in_progress(self):
        """
        Limit the QuerySet to ResourceURI being processed.

        Also include ResourceURI that failed to be processed completely properly
        and have a wip_date that was not reset to null once their processing
        finished, such as after a failure or exception.
        """
        return self.filter(wip_date__isnull=False)

    def needs_revisit(self, uri, hours):
        """
        Return True if the uri has not been visited since the number of `hours`, and
        therefore needs to be re-visited.
        """
        existing = self.never_visited().filter(uri=uri).exists()
        if existing:
            return False

        revisitable = self.get_revisitables(hours=hours).filter(uri=uri).exists()
        if revisitable:
            return True
        else:
            return False

    def never_visited(self):
        """
        Limit the QuerySet to ResourceURIs that have never been visited.
        This is usually the state of a ResourceURI after upon creation.
        """
        return self.filter(last_visit_date__isnull=True, wip_date__isnull=True)

    def visited(self):
        """
        Limit the QuerySet to ResourceURIs that were visited irrespective of
        success or errors during their visit.
        """
        return self.filter(wip_date__isnull=True, last_visit_date__isnull=False)

    def successfully_visited(self):
        """
        Limit the QuerySet to ResourceURIs that were visited successfully.
        """
        return self.visited().filter(visit_error__isnull=True)

    def unsuccessfully_visited(self):
        """
        Limit the QuerySet to ResourceURIs that were visited with errors.
        """
        return self.visited().filter(visit_error__isnull=False)

    def get_revisitables(self, hours):
        """
        Limit the QuerySet to ResourceURIs that have not been visited since the number
        of `hours`, and therefore considered revisitable.
        """
        revisitables = self.visited().filter(
            last_visit_date__lt=timezone.now() - timedelta(hours=hours)
        ).exclude(
            is_mappable=True, last_map_date__isnull=True
        )

        return revisitables

    def get_visitables(self):
        """
        Return an ordered query set of all visitable ResourceURIs.
        Note: this does not evaluate the query set and does not lock the
        database for update.
        """
        never_visited = self.never_visited().filter(is_visitable__exact=True)
        revisitables = self.get_revisitables(hours=240)

        if revisitables:
            visitables = never_visited.union(revisitables)
        else:
            visitables = never_visited

        # NOTE: this matches an index for efficient ordering
        visitables = visitables.order_by('-priority', '-uri')
        return visitables

    def get_next_visitable(self):
        """
        Return the next ResourceURI candidate for visit and mark it as
        being "in_progress" by setting the wip_date field.
        Return None when there is no candidate left to visit.

        NOTE: this method can only be called from within a
        transaction.atomic block.

        Note: the ResourceURI table is used as a queue that can be
        sorted by priority and tracks the status of visits of each
        ResourceURI. ResourceURI that have not yet been visited are
        sorted by decreasing priority.
        """

        # We use select_for_update to ensure an atomic query. We ignore
        # locked rows by using skip_locked=True available since Django
        # 1.11.

        # Locked row are being updated in other workers and therefore
        # there is nothing to do with these. This is a great way to get
        # an efficient queue in a model.

        # Per Postgres doc:
        # With SKIP LOCKED, any selected rows that cannot be immediately
        # locked are skipped. Skipping locked rows provides an
        # inconsistent view of the data, so this is not suitable for
        # general purpose work, but can be used to avoid lock contention
        # with multiple consumers accessing a queue-like table.
        visitables = self.get_visitables().select_for_update(skip_locked=True)

        # keep the top record if there is one
        resource_uris = visitables[:1]

        # This force the evaluation of the query but only once
        # (previously exists then get was evaluating two QS)
        resource_uris = list(resource_uris)
        if not resource_uris:
            return

        resource_uri = resource_uris[0]

        # Mark the URI as wip: Callers mark this done by resetting
        # wip_date to null
        resource_uri.wip_date = timezone.now()
        resource_uri.save(update_fields=['wip_date'])
        return resource_uri

    def never_mapped(self):
        """
        Limit the QuerySet to ResourceURIs that have never been mapped.
        This is usually the state of a ResourceURI after its succesful visit.
        """
        return self.successfully_visited().filter(last_map_date__isnull=True, wip_date__isnull=True)

    def mapped(self):
        """
        Limit the QuerySet to ResourceURIs that were mapped irrespective of
        success or errors during their visit.
        """
        return self.filter(wip_date__isnull=True, last_map_date__isnull=False)

    def successfully_mapped(self):
        """
        Limit the QuerySet to ResourceURIs that were mapped successfully.
        """
        return self.mapped().filter(map_error__isnull=True)

    def unsuccessfully_mapped(self):
        """
        Limit the QuerySet to ResourceURIs that were mapped with errors.
        """
        return self.mapped().filter(map_error__isnull=False)

    def get_mappables(self):
        """
        Return an ordered query set of all mappable ResourceURIs.
        Note: this does not evaluate the query set and does not lock the
        database for update.
        """
        qs = self.never_mapped().filter(is_mappable__exact=True, map_error__isnull=True)
        # NOTE: this matches an index for efficient ordering
        qs = qs.order_by('-priority')
        return qs


class ResourceURI(BaseURI):
    """
    Stores URI that are crawled (aka. visited) and the progress of this process.
    Also used as a processing "to do" queue for visiting and mapping these URIs.

    The states of a ResourceURI are based on multiple "last_xxxx_date"
    timestamps and "is_xxxable" flags.

    The standard lifecycle of a ResourceURI that contains package metadata is:
     - at creation it is "is_visitable" if there is a visitor for it (e.g. it is eligible for visiting.)
     - when the visit starts, the "wip_date" is set. The visiting takes place.
     - once the visit is done, the "wip_date" is reset. The "last_visit_date" is set.
     - If "is_mappable" and the visit was done without "visit_errors", the mapping starts.
     - when the mapping starts, the "wip_date" is set. The mapping takes place.
     - once the mapping is done, the "wip_date" is reset. The "last_map_date" is set.
    """

    mining_level = models.PositiveIntegerField(
        default=0,
        help_text='A numeric indication of the depth and breadth of data '
                  'collected through this ResourceURI visit. Higher means '
                  'more and deeper data.',
    )

    # This is a text blob that contains either HTML, JSON or anything
    # stored as a string. This is the raw content of visiting a URI.
    # NOTE: some visited URLS (such as an actual package archive will/shoud NOT be stored there)
    data = models.TextField(
        null=True,
        blank=True,
        help_text='Text content of the file represented by this '
                  'ResourceURI. This contains the data that was fetched or '
                  'extracted from a remote ResourceURI such as HTML or JSON.',
    )

    package_url = models.CharField(
        max_length=2048,
        null=True,
        blank=True,
        db_index=True,
        help_text="""Package URL for this resource. It stands for a package "mostly universal" URL."""
    )

    last_visit_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Timestamp set to the date of the last visit.  Used to track visit status.',
    )

    is_visitable = models.BooleanField(
        db_index=True,
        default=False,
        help_text='When set to True (Yes), this field indicates that '
                  'this URI is visitable in the sense that there is a visitor '
                  'route available to process it.'
    )

    visit_error = models.TextField(
        null=True,
        blank=True,
        help_text='Visit errors messages. When present this means the visit failed.',
    )

    last_map_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Timestamp set to the date of the last mapping. '
                  'Used to track mapping status.',
    )

    is_mappable = models.BooleanField(
        db_index=True,
        default=False,
        help_text='When set to True (Yes), this field indicates that '
        'this URI is mappable in the sense that there is a mapper '
        'route available to process it.'
    )

    map_error = models.TextField(
        null=True,
        blank=True,
        help_text='Mapping errors messages. When present this means the mapping failed.',
    )

    objects = ResourceURIManager()

    class Meta:
        verbose_name = 'Resource URI'
        unique_together = ['canonical', 'last_visit_date']

        indexes = [
            # to get the next visitable
            models.Index(
                fields=['is_visitable', 'last_visit_date', 'wip_date']),
            # to get the next mappable
            models.Index(
                fields=['is_mappable', 'last_visit_date', 'wip_date', 'last_map_date', 'visit_error']),
            # ordered by for the main queue query e.g. '-priority'
            models.Index(
                fields=['-priority'])
        ]

    def _set_defauts(self):
        """
        Set defaults for computed fields.
        """
        uri = self.uri
        if not self.canonical:
            self.canonical = get_canonical(uri)
        self.is_visitable = visit_router.is_routable(uri)
        self.is_mappable = map_router.is_routable(uri)

    def save(self, *args, **kwargs):
        """
        Save, adding defaults for computed fields and validating fields.
        """
        self._set_defauts()
        self.normalize_fields()
        super(ResourceURI, self).save(*args, **kwargs)


class ScannableURIManager(models.Manager):
    def get_scannables(self):
        """
        Return an ordered query set of all scannable ScannableURIs.
        Note: this does not evaluate the query set and does not lock the
        database for update.
        """
        qs = self.filter(scan_status__exact=ScannableURI.SCAN_NEW,
                         wip_date=None, scan_error=None)
        # NOTE: this matches an index for efficient ordering
        qs = qs.order_by('-priority')
        return qs

    def get_next_scannable(self):
        """
        Return the next ScannableURI candidate for scan and mark it as
        being "processed" by setting the wip_date field.
        Return None when there is no candidate left to scan.

        NOTE: this method can only be called from within a
        transaction.atomic block.
        """
        return self.__get_next_candidate(self.get_scannables())

    def __get_next_candidate(self, qs):
        """
        Return and "lock" the next candidate ScannableURI from the `qs` query
        set or None.

        Mark it as being "processed" by setting the wip_date field. Return None
        when there is no candidate left.

        Note: this table is used as a queue that can be
        sorted by priority and tracks the status of scan requests.
        URI that have not yet been requested for scan are
        sorted by decreasing priority.
        """
        # FIXME: use a shared function for this

        # We use select_for_update to ensure an atomic query. We ignore
        # locked rows by using skip_locked=True available since Django
        # 1.11.

        # Locked row are being updated in other workers and therefore
        # there is nothing to do with these. This is a great way to get
        # an efficient queue in a model.

        # Per Postgres doc:
        # With SKIP LOCKED, any selected rows that cannot be immediately
        # locked are skipped. Skipping locked rows provides an
        # inconsistent view of the data, so this is not suitable for
        # general purpose work, but can be used to avoid lock contention
        # with multiple consumers accessing a queue-like table.
        candidate_uris = qs.select_for_update(skip_locked=True)

        # keep the top record if there is one
        candidate_uris = candidate_uris[:1]

        # This force the evaluation of the query but only once
        # (previously exists then get was evaluating two QS)
        candidate_uris = list(candidate_uris)
        if not candidate_uris:
            return

        canidate_uri = candidate_uris[0]

        # Mark the URI as wip: Callers mark this done by resetting
        # wip_date to null
        canidate_uri.wip_date = timezone.now()
        canidate_uri.save(update_fields=['wip_date'])
        return canidate_uri

    def get_processables(self):
        """
        Return an ordered query set of all "processable" ScannableURIs that have
        been submitted and are in a state where they can be processed.

        Note: this does not evaluate the query set and does not lock the
        database for update.
        """
        qs = self.filter(scan_status__in=[
                ScannableURI.SCAN_SUBMITTED,
                ScannableURI.SCAN_IN_PROGRESS,
                ScannableURI.SCAN_COMPLETED
            ],
            wip_date=None, scan_error=None,
        )
        # NOTE: this matches an index for efficient ordering
        qs = qs.order_by('-scan_status', '-priority')
        return qs

    def get_next_processable(self):
        """
        Return the next ScannableURI candidate for visit and mark it as
        being "in_progress" by setting the wip_date field.
        Return None when there is no candidate left to visit.

        NOTE: this method can only be called from within a
        transaction.atomic block.
        """
        return self.__get_next_candidate(self.get_processables())


class ScannableURI(BaseURI):
    """
    Stores URLs for downloadable packages to scan.
    Used as a processing "to do" queue for controlling scanning of these URLs.

    The lifecycle of a ScannableURI is:
     - at creation its "request_date" is empty and scan_status is "new" (e.g. ready to scan)
     - the scan worker selects one URI ready to scan based on various criteria then,
       - submit the API to the scancode.io server scan API
       - the scancode.io server sends back a "scan_uuid" which is set in this URI
         The scanning takes place remotely.
       - the "scan_request_date" is set
       - the "scan_status" is set to "submitted"

     - a worker checks all the scans that are "submitted" and have a
       "scan_request_date" that is older than a certain waiting time (say 10 to 20
       minutes) and for each ScannbleURI
       - send a get request to the scancode.io server for the "scan_uuid"
       - based on the received API data:
         - if the scan completed, the status is updated to completed or failed,
           the scan_error is updated if needed
         - if the scan is not completed, the status is updated accordingly and
           the last_status_poll_date is set.
           - if the time elapsed since the scan_request_date is too large, the
             status is set to timeout.

     - an index worker checks all the scans that are "completed" and have no error
       and for each ScannbleURI
        - calls scancode.io API to fetch the scan referenced by the "scan_uuid" (and store it temporarily)
        - update the PackageDB as needed with "meta" data from the scan
        - update the matching index for the PackageDB as needed with fingerprints from the scan
        - set status and timestamps as needed
    """
    scan_request_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Timestamp set to the date when a scan was requested.  Used to track scan status.',
    )

    last_status_poll_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Timestamp set to the date of the last status poll. '
                  'Used to track the scan polling.',
    )

    scan_uuid = models.CharField(
        max_length=36,
        blank=True,
        null=True,
        db_index=True,
        help_text='UUID of a scan for this URI in ScanCode.io.',
    )

    SCAN_NEW = 0
    SCAN_SUBMITTED = 1
    SCAN_IN_PROGRESS = 2
    SCAN_COMPLETED = 3
    SCAN_INDEXED = 4
    SCAN_FAILED = 5
    SCAN_TIMEOUT = 6
    SCAN_INDEX_FAILED = 7

    SCAN_STATUS_CHOICES = [
        (SCAN_NEW, 'new'),
        (SCAN_SUBMITTED, 'submitted'),
        (SCAN_IN_PROGRESS, 'in progress'),
        (SCAN_COMPLETED, 'scanned'),
        (SCAN_INDEXED, 'indexed'),
        (SCAN_FAILED, 'failed'),
        (SCAN_TIMEOUT, 'timeout'),
        (SCAN_INDEX_FAILED, 'scan index failed')
    ]

    SCAN_STATUSES_BY_CODE = dict(SCAN_STATUS_CHOICES)

    scan_status = models.IntegerField(
        default=SCAN_NEW,
        choices=SCAN_STATUS_CHOICES,
        db_index=True,
        help_text='Status of the scan for this URI.',
    )

    scan_uuid = models.CharField(
        max_length=36,
        blank=True,
        null=True,
        db_index=True,
        help_text='UUID of a scan for this URI in ScanCode.io.',
    )

    scan_error = models.TextField(
        null=True,
        blank=True,
        help_text='Scan errors messages. When present this means the scan failed.',
    )

    index_error = models.TextField(
        null=True,
        blank=True,
        help_text='Indexing errors messages. When present this means the indexing failed.',
    )

    package = models.ForeignKey(
        Package,
        help_text='The Package that this ScannableURI is for',
        on_delete=models.CASCADE,
        null=False,
    )

    objects = ScannableURIManager()

    class Meta:
        verbose_name = 'Scannable URI'
        unique_together = ['canonical', 'scan_uuid']

        indexes = [
            # to get the scannables
            models.Index(
                fields=['scan_status', 'scan_request_date', 'last_status_poll_date', ]),
            # ordered by for the main queue query e.g. '-priority'
            models.Index(
                fields=['-priority'])
        ]

    def save(self, *args, **kwargs):
        """
        Save, adding defaults for computed fields and validating fields.
        """
        if not self.canonical:
            self.canonical = get_canonical(self.uri)
        self.normalize_fields()
        super(ScannableURI, self).save(*args, **kwargs)
