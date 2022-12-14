#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from collections import defaultdict
from datetime import datetime
import binascii
import logging
import sys

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from matchcode.fingerprinting import create_halohash_chunks
from matchcode.fingerprinting import split_fingerprint
from matchcode.halohash import byte_hamming_distance
from matchcode.utils import get_error_message
from matchcode.utils import hexstring_to_binarray

from packagedb.models import Package
from packagedb.models import Resource


TRACE = False

if TRACE:
    level = logging.DEBUG
else:
    level = logging.ERROR

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout)
logger.setLevel(level)


def logger_debug(*args):
    return logger.debug(' '.join(isinstance(a, str) and a or repr(a) for a in args))


###############################################################################
# FILE MATCHING
###############################################################################
class BaseFileIndex(models.Model):
    sha1 = models.BinaryField(
        max_length=20,
        db_index=True,
        help_text='Binary form of a SHA1 checksum in lowercase hex for a file',
        null=False,
        blank=False,
    )

    package = models.ForeignKey(
        Package,
        help_text='The Package that this file is from',
        null=False,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True

    @classmethod
    def index(cls, sha1, package):
        try:
            sha1_bin = hexstring_to_binarray(sha1)
            bfi, created = cls.objects.get_or_create(
                package=package,
                sha1=sha1_bin
            )
            if created:
                logger.info(
                    '{} - Inserted {} for Package {}:\t{}'.format(
                        datetime.utcnow().isoformat(),
                        bfi.__class__.__name__,
                        package.download_url,
                        sha1
                    )
                )
            return bfi, created
        except Exception as e:
            msg = f'Error creating {bfi.__class__.__name__}:\n'
            msg += get_error_message(e)
            package.index_error = msg
            package.save()
            logger.error(msg)

    @classmethod
    def match(cls, sha1):
        """
        Return a list of matched Packages that contains a file with a SHA1 value of `sha1`
        """
        if TRACE:
            logger_debug(cls.__name__, 'match:', 'sha1:', sha1)

        if not sha1:
            return cls.objects.none()

        sha1_in_bin = hexstring_to_binarray(sha1)
        matches = cls.objects.filter(sha1=sha1_in_bin)
        if TRACE:
            for match in matches:
                package = match.package
                dct = model_to_dict(package)
                logger_debug(cls.__name__, 'match:', 'matched_file:', dct)
        return matches

    def fingerprint(self):
        return binascii.hexlify(self.sha1).decode('utf-8')


class ExactPackageArchiveIndex(BaseFileIndex):
    pass


class ExactFileIndex(BaseFileIndex):
    pass


################################################################################
# DIRECTORY MATCHING
################################################################################
def bah128_ranges(indexed_elements_count, range_ratio=0.05):
    """
    Return a tuple of two integers, one smaller than `indexed_elements_count` by
    `range_ratio` and one larger than `indexed_elements_count` by `range_ratio`

    This helps us match on directories with similar amounts of files. Directory
    fingerprints become uncomparable if one fingerprint has more elements
    indexed in it than another.
    """
    return (
        int(indexed_elements_count * (1 - range_ratio)),
        int(indexed_elements_count * (1 + range_ratio))
    )


class BaseDirectoryIndex(models.Model):
    indexed_elements_count = models.IntegerField(
        help_text='Number of elements that went into the fingerprint',
    )

    chunk1 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text='Binary form of the first 8 (0-7) hex digits of the fingerprint',
        null=False,
        blank=False
    )

    chunk2 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text='Binary form of the second 8 (8-15) hex digits of the fingerprint',
        null=False,
        blank=False
    )

    chunk3 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text='Binary form of the third 8 (16-23) hex digits of the fingerprint',
        null=False,
        blank=False
    )

    chunk4 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text='Binary form of the fourth 8 (24-32) hex digits of the fingerprint',
        null=False,
        blank=False
    )

    package = models.ForeignKey(
        Package,
        help_text='The Package that this directory is a part of',
        null=False,
        on_delete=models.CASCADE,
    )

    path = models.CharField(
        max_length=2000,
        help_text=_('The full path value of this directory'),
    )

    class Meta:
        abstract = True
        unique_together = ['chunk1', 'chunk2', 'chunk3', 'chunk4', 'package', 'path']

    def __str__(self):
        return self.fingerprint()

    @classmethod
    def index(cls, directory_fingerprint, resource_path, package):
        """
        Index the string `directory_fingerprint` into the BaseDirectoryIndex model
        """
        try:
            indexed_elements_count, fp = split_fingerprint(directory_fingerprint)
            fp_chunk1, fp_chunk2, fp_chunk3, fp_chunk4 = create_halohash_chunks(fp)
            bdi, created = cls.objects.get_or_create(
                indexed_elements_count=indexed_elements_count,
                chunk1=fp_chunk1,
                chunk2=fp_chunk2,
                chunk3=fp_chunk3,
                chunk4=fp_chunk4,
                path=resource_path,
                package=package,
            )
            if created:
                logger.info(
                    '{} - Inserted {} for Package {}:\t{}'.format(
                        datetime.utcnow().isoformat(),
                        bdi.__class__.__name__,
                        package.download_url,
                        directory_fingerprint
                    )
                )
            return bdi, created
        except Exception as e:
            msg = f'Error creating {bdi.__class__.__name__}:\n'
            msg += get_error_message(e)
            package.index_error = msg
            package.save()
            logger.error(msg)

    @classmethod
    def match(cls, directory_fingerprint):
        """
        Return a list of matched Packages
        """
        if TRACE:
            logger_debug(cls.__name__, 'match:', 'directory_fingerprint:', directory_fingerprint)

        if not directory_fingerprint:
            return cls.objects.none()

        # Step 1: find fingerprints with matching chunks
        indexed_elements_count, bah128 = split_fingerprint(directory_fingerprint)
        chunk1, chunk2, chunk3, chunk4 = create_halohash_chunks(bah128)
        range = bah128_ranges(indexed_elements_count)
        matches = cls.objects.filter(
            models.Q(
                indexed_elements_count__range=range,
                chunk1=chunk1
            ) |
            models.Q(
                indexed_elements_count__range=range,
                chunk2=chunk2
            ) |
            models.Q(
                indexed_elements_count__range=range,
                chunk3=chunk3
            ) |
            models.Q(
                indexed_elements_count__range=range,
                chunk4=chunk4
            )
        )

        if TRACE:
            for match in matches:
                dct = model_to_dict(match)
                logger_debug(cls.__name__, 'match:', 'matched_package:', dct)

        # Step 2: calculate Hamming distance of all matches

        # Store all close matches in a dictionary of querysets
        matches_by_hamming_distance = defaultdict(cls.objects.none)
        for match in matches:
            # Get fingerprint from the match
            fp = match.fingerprint()
            _, match_bah128 = split_fingerprint(fp)

            # Perform Hamming distance calculation between the fingerprint we
            # are looking up and a potential match fingerprint
            hd = byte_hamming_distance(bah128, match_bah128)

            # TODO: try other thresholds if this is too restrictive
            if hd < 8:
                # Save match to `matches_by_hamming_distance` by adding the matched object to the queryset
                matches_by_hamming_distance[hd] |= cls.objects.filter(pk=match.pk)

        if TRACE:
            logger_debug(list(matches_by_hamming_distance.items()))

        # Step 3: order matches from lowest Hamming distance to highest Hamming distance
        # TODO: consider limiting matches for brevity
        good_matches = cls.objects.none()
        for hamming_distance, match in sorted(matches_by_hamming_distance.items()):
            if hamming_distance == 0:
                # If we have an exact match, return and disregard others
                good_matches |= match
                break
            else:
                # If we don't have an exact match, add all close matches we have
                good_matches |= match

        if TRACE:
            for match in good_matches:
                dct = model_to_dict(match)
                logger_debug(cls.__name__, 'match:', 'good_matched_package:', dct)

        return good_matches

    def get_chunks(self):
        chunk1 = binascii.hexlify(self.chunk1)
        chunk2 = binascii.hexlify(self.chunk2)
        chunk3 = binascii.hexlify(self.chunk3)
        chunk4 = binascii.hexlify(self.chunk4)
        return chunk1, chunk2, chunk3, chunk4

    def fingerprint(self):
        indexed_element_count_as_hex_bytes = b'%08x' % self.indexed_elements_count
        chunk1, chunk2, chunk3, chunk4 = self.get_chunks()
        fingerprint = indexed_element_count_as_hex_bytes + chunk1 + chunk2 + chunk3 + chunk4
        return fingerprint.decode('utf-8')


class ApproximateDirectoryStructureIndex(BaseDirectoryIndex):
    pass


class ApproximateDirectoryContentIndex(BaseDirectoryIndex):
    pass
