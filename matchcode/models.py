#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import binascii
import logging
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import NamedTuple

from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _

import attr
from licensedcode.spans import Span
from matchcode_toolkit.fingerprinting import create_halohash_chunks
from matchcode_toolkit.fingerprinting import hexstring_to_binarray
from matchcode_toolkit.fingerprinting import split_fingerprint
from samecode.halohash import byte_hamming_distance

from minecode.management.commands import get_error_message
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
    return logger.debug(" ".join(isinstance(a, str) and a or repr(a) for a in args))


class PackageRelatedMixin(models.Model):
    package = models.ForeignKey(
        Package,
        help_text="The Package that this file is from",
        null=False,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


###############################################################################
# FILE MATCHING
###############################################################################
class BaseFileIndex(PackageRelatedMixin, models.Model):
    sha1 = models.BinaryField(
        max_length=20,
        db_index=True,
        help_text="Binary form of a SHA1 checksum in lowercase hex for a file",
        null=False,
        blank=False,
    )

    class Meta:
        abstract = True

    @classmethod
    def index(cls, sha1, package):
        try:
            sha1_bin = hexstring_to_binarray(sha1)
            bfi, created = cls.objects.get_or_create(package=package, sha1=sha1_bin)
            if created:
                logger.info(
                    f"{datetime.utcnow().isoformat()} - Inserted {bfi.__class__.__name__} for Package {package.download_url}:\t{sha1}"
                )
            return bfi, created
        except Exception as e:
            msg = "Error creating FileIndex:\n"
            msg += get_error_message(e)
            package.index_error = msg
            package.save()
            logger.error(msg)

    @classmethod
    def match(cls, sha1):
        """Return a list of matched Packages that contains a file with a SHA1 value of `sha1`"""
        if TRACE:
            logger_debug(cls.__name__, "match:", "sha1:", sha1)

        if not sha1:
            return cls.objects.none()

        sha1_in_bin = hexstring_to_binarray(sha1)
        matches = cls.objects.filter(sha1=sha1_in_bin)
        if TRACE:
            for match in matches:
                package = match.package
                dct = model_to_dict(package)
                logger_debug(cls.__name__, "match:", "matched_file:", dct)
        return matches

    def fingerprint(self):
        return binascii.hexlify(self.sha1).decode("utf-8")


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
        int(indexed_elements_count * (1 + range_ratio)),
    )


class ApproximateMatchingHashMixin(PackageRelatedMixin, models.Model):
    indexed_elements_count = models.IntegerField(
        help_text="Number of elements that went into the fingerprint",
    )

    chunk1 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text="Binary form of the first 8 (0-7) hex digits of the fingerprint",
        null=False,
        blank=False,
    )

    chunk2 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text="Binary form of the second 8 (8-15) hex digits of the fingerprint",
        null=False,
        blank=False,
    )

    chunk3 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text="Binary form of the third 8 (16-23) hex digits of the fingerprint",
        null=False,
        blank=False,
    )

    chunk4 = models.BinaryField(
        max_length=4,
        db_index=True,
        help_text="Binary form of the fourth 8 (24-32) hex digits of the fingerprint",
        null=False,
        blank=False,
    )

    path = models.CharField(
        max_length=2000,
        help_text=_("The full path value of this resource"),
    )

    class Meta:
        abstract = True
        unique_together = ["chunk1", "chunk2", "chunk3", "chunk4", "package", "path"]

    def __str__(self):
        return self.fingerprint()

    @classmethod
    def index(cls, fingerprint, resource_path, package):
        """
        Index the string `fingerprint` into the ApproximateMatchingHashMixin
        model

        Return a 2-tuple of the corresponding ApproximateMatchingHashMixin
        created from `fingerprint` and a boolean, which represents whether the
        fingerprint was created or not.
        """
        try:
            indexed_elements_count, fp = split_fingerprint(fingerprint)
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
                    f"{datetime.utcnow().isoformat()} - Inserted {bdi.__class__.__name__} "
                    f"for Package {package.download_url}:\t{fingerprint}"
                )
            return bdi, created
        except Exception as e:
            msg = "Error creating ApproximateMatchingHashMixin:\n"
            msg += get_error_message(e)
            package.index_error = msg
            package.save()
            logger.error(msg)

    @classmethod
    def match(cls, fingerprint, resource=None, exact_match=False):
        """Return a list of matched Packages"""
        if TRACE:
            logger_debug(
                cls.__name__,
                "match:",
                "fingerprint:",
                fingerprint,
                "resource:",
                resource,
            )

        if not fingerprint:
            return cls.objects.none()

        indexed_elements_count, bah128 = split_fingerprint(fingerprint)
        chunk1, chunk2, chunk3, chunk4 = create_halohash_chunks(bah128)

        # Step 0: if exact only, then return a filter
        if exact_match:
            matches = cls.objects.filter(
                indexed_elements_count=indexed_elements_count,
                chunk1=chunk1,
                chunk2=chunk2,
                chunk3=chunk3,
                chunk4=chunk4,
            )
            return matches

        # Step 1: find fingerprints with matching chunks
        frange = bah128_ranges(indexed_elements_count)
        matches = cls.objects.filter(
            models.Q(indexed_elements_count__range=frange, chunk1=chunk1)
            | models.Q(indexed_elements_count__range=frange, chunk2=chunk2)
            | models.Q(indexed_elements_count__range=frange, chunk3=chunk3)
            | models.Q(indexed_elements_count__range=frange, chunk4=chunk4)
        )

        if TRACE:
            for match in matches:
                dct = model_to_dict(match)
                logger_debug(cls.__name__, "match:", "matched_package:", dct)

        # Step 2: calculate Hamming distance of all matches

        hamming_distance_threshold = 10
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
            # TODO: rank matches instead of having threshold
            if hd < hamming_distance_threshold:
                # Save match to `matches_by_hamming_distance` by adding the matched object
                # to the queryset
                matches_by_hamming_distance[hd] |= cls.objects.filter(pk=match.pk)

        if TRACE:
            logger_debug(list(matches_by_hamming_distance.items()))

        # Step 3: order matches from lowest Hamming distance to highest Hamming distance
        # TODO: consider limiting matches for brevity
        hamming_distances_and_matches = []
        for hamming_distance, matches in sorted(matches_by_hamming_distance.items()):
            hamming_distances_and_matches.append((hamming_distance, matches))

        if TRACE:
            for hamming_distance, matches in hamming_distances_and_matches:
                for match in matches:
                    dct = model_to_dict(match)
                    logger_debug(
                        cls.__name__,
                        "match:",
                        "step_3_hamming_distance:",
                        hamming_distance,
                        "step_3_matched_package:",
                        dct,
                    )

        # Step 4: use file heuristics to rank matches from step 3

        # If we are not given resource data, return the matches we have
        if not (resource and hamming_distances_and_matches):
            remaining_matches = cls.objects.none()
            if hamming_distances_and_matches:
                for _, matches in hamming_distances_and_matches:
                    remaining_matches |= matches
            return remaining_matches

        resource_size = resource.size
        matches_by_rank_attributes = defaultdict(list)
        for hamming_distance, matches in hamming_distances_and_matches:
            for match in matches:
                matched_resource = match.package.resources.get(path=match.path)

                if TRACE:
                    logger_debug(
                        cls.__name__,
                        "match:",
                        "step_4_matched_resource:",
                        matched_resource,
                    )

                # Compute size and name difference
                if matched_resource.is_file:
                    size_difference = abs(resource_size - matched_resource.size)
                else:
                    # TODO: index number of files in a directory so we can use
                    # that for size comparison. For now, we are going to
                    # disregard size as a factor.
                    size_difference = 0
                name_sequence_matcher = SequenceMatcher(
                    a=resource.name, b=matched_resource.name
                )
                name_difference = 1 - name_sequence_matcher.ratio()
                rank_attributes = (hamming_distance, size_difference, name_difference)
                matches_by_rank_attributes[rank_attributes].append(match)

                if TRACE:
                    logger_debug(
                        cls.__name__,
                        "match:",
                        "step_4_size_difference:",
                        size_difference,
                        "step_4_name_difference:",
                        name_difference,
                    )

        # Order these from low to high (low being low difference/very similar)),
        # first by hamming distance, then by size difference, and finally by name difference.
        ranked_attributes = sorted(matches_by_rank_attributes)
        best_ranked_attributes = ranked_attributes[0]
        ranked_matches = matches_by_rank_attributes[best_ranked_attributes]

        if TRACE:
            dct = model_to_dict(match)
            logger_debug(cls.__name__, "match:", "step_4_best_match:", dct)

        matches = cls.objects.filter(pk__in=[match.pk for match in ranked_matches])
        return matches

    def get_chunks(self):
        chunk1 = binascii.hexlify(self.chunk1)
        chunk2 = binascii.hexlify(self.chunk2)
        chunk3 = binascii.hexlify(self.chunk3)
        chunk4 = binascii.hexlify(self.chunk4)
        return chunk1, chunk2, chunk3, chunk4

    def fingerprint(self):
        indexed_element_count_as_hex_bytes = b"%08x" % self.indexed_elements_count
        chunk1, chunk2, chunk3, chunk4 = self.get_chunks()
        fingerprint = (
            indexed_element_count_as_hex_bytes + chunk1 + chunk2 + chunk3 + chunk4
        )
        return fingerprint.decode("utf-8")


class ApproximateDirectoryStructureIndex(ApproximateMatchingHashMixin):
    pass


class ApproximateDirectoryContentIndex(ApproximateMatchingHashMixin):
    pass


class ApproximateResourceContentIndex(ApproximateMatchingHashMixin):
    pass


class PackageSnippetMatch(NamedTuple):
    package: Package
    fingerprints: list["SnippetIndex"]
    fingerprints_count: int


class ResourceSnippetMatch(NamedTuple):
    resource: Resource
    package: Package
    fingerprints: list["SnippetIndex"]
    fingerprints_count: int
    similarity: float


class SnippetIndex(PackageRelatedMixin, models.Model):
    resource = models.ForeignKey(
        Resource,
        help_text="The Package that this snippet fingerprint is from",
        null=False,
        on_delete=models.CASCADE,
    )

    fingerprint = models.BinaryField(
        max_length=16,
        db_index=True,
        help_text="Binary form of a snippet fingerprint",
        null=False,
        blank=False,
    )

    position = models.PositiveIntegerField(
        null=False,
        blank=False,
        default=0,
    )

    # TODO: window length must be constant so we can calculate offsets

    @classmethod
    def index(cls, fingerprint, position, resource, package):
        """
        Index the string `fingerprint` into the SnippetIndex model.

        Return a 2-tuple of the corresponding SnippetIndex created from
        `fingerprint` and a boolean, which represents whether the fingerprint
        was created or not.
        """
        try:
            fp = hexstring_to_binarray(fingerprint)
            hi, created = cls.objects.get_or_create(
                package=package,
                position=position,
                resource=resource,
                fingerprint=fp,
            )
            if created:
                logger.info(
                    f"{datetime.utcnow().isoformat()} - Inserted {hi.__class__.__name__} "
                    f"for Resource {resource.path} from Package {package.download_url}:\t{fingerprint}"
                )
                return hi, created
        except Exception as e:
            msg = "Error creating SnippetIndex:\n"
            msg += get_error_message(e)
            package.index_error = msg
            package.save()
            logger.error(msg)

    @classmethod
    def match(cls, fingerprints):
        """
        Return a list of PackageSnippetMatch for matched Package.
        """
        if TRACE:
            logger_debug(
                cls.__name__,
                "match:",
                "fingerprints:",
                fingerprints,
            )

        if not fingerprints:
            return cls.objects.none()

        # strip positions
        only_fings = [hexstring_to_binarray(fing["snippet"]) for fing in fingerprints]

        # Step 0: get all fingerprint records that match whith the input
        matched_fps = cls.objects.filter(fingerprint__in=only_fings)

        # Step 1: count Packages whose fingerprints appear
        # Step 1.1: get Packages that show up in the query
        packages = set(f.package for f in matched_fps.iterator())

        # Step 1.2: group matched Packages and fingerprints with count
        matches = []
        for package in packages:
            match_fingerprints = matched_fps.filter(package=package)
            matches.append(
                PackageSnippetMatch(
                    package=package,
                    fingerprints=match_fingerprints,
                    fingerprints_count=match_fingerprints.count(),
                )
            )

        return matches

    @classmethod
    def match_resources(cls, fingerprints, top=None):
        """
        Return a list of ResourceSnippetMatch for matched Resources.
        Only return the ``top`` matches, or all matches if ``top`` is zero.
        """
        if TRACE:
            logger_debug(
                cls.__name__,
                "match:",
                "fingerprints:",
                fingerprints,
            )

        if not fingerprints:
            return cls.objects.none()

        # strip positions
        only_fings = [hexstring_to_binarray(fing["snippet"]) for fing in fingerprints]

        # Step 0: get all fingerprint records that match whith the input
        matched_fps = cls.objects.filter(fingerprint__in=only_fings)

        # Step 1: get Resources that show up in the query
        resources = set(f.resource for f in matched_fps.iterator())

        # Step 2: see which Resource we most match to by calculating jaccard coefficient of our fingerprints against the others
        fingerprints_length = len(only_fings)
        matches_by_jc = defaultdict(list)
        for r in resources:
            # Get unique snippet fingerprints for this Resource
            r_snippets = (
                SnippetIndex.objects.filter(resource=r).distinct("fingerprint")
            )
            matching_snippets = r_snippets.filter(fingerprint__in=only_fings)
            r_snippets_count = r_snippets.count()
            matching_snippets_count = matching_snippets.count()
            jc = matching_snippets_count / (
                (r_snippets_count + fingerprints_length) - matching_snippets_count
            )
            matches_by_jc[jc].append(
                ResourceSnippetMatch(
                    resource=r,
                    package=r.package,
                    fingerprints=matching_snippets,
                    fingerprints_count=matching_snippets_count,
                    similarity=jc,
                )
            )

        # Step 3: order results from highest coefficient to lowest
        matches = []
        for jc, m in sorted(matches_by_jc.items(), reverse=True):
            matches.extend(m)

        return matches[:top]


class ApproximateFileIndex(ApproximateMatchingHashMixin, models.Model):
    pass


@attr.s(slots=True, eq=False, order=False, repr=False)
class ExtendedFileFragmentMatch:
    """
    A File origin detection match to an index Resource with matched query positions, lines and
    matched index positions. This also computes a score for a match. At a high level,
    a match behaves a little like a Span/interval and has several similar methods taking
    into account both the query (codebase-side) and index-side Spans.

    Note that the relationship between the query-side qspan Span and the index-
    side ispan Span is such that:

    - they always have the exact same number of items but when sorted each
      value at a given index may be different
    - the nth position when sorted by position is such that their token
      value is equal for this position.

    These properties mean that the qspan and ispan can be safely zipped together with
    zip() to align them. Also and as a convention throughout, we always use qspan first then
    ispan: in general we put codebase/query-related variables on the left hand side and
    index-related variables on the right hand side.
    """

    qresource = attr.ib(
        type=Resource, metadata=dict(help="matched from query-side Resource")
    )

    iresource = attr.ib(
        type=Resource, metadata=dict(help="matched to index-side Resource")
    )

    qspan = attr.ib(
        metadata=dict(
            help="query matched Span, start at zero which is the query Resource start."
        )
    )

    ispan = attr.ib(
        metadata=dict(
            help="index side matched Span, start at zero which is the indexed Resource start."
        )
    )

    start_line = attr.ib(default=0, metadata=dict(help="match start line, 1-based"))

    end_line = attr.ib(default=0, metadata=dict(help="match end line, 1-based"))

    def __repr__(self):
        qreg = (self.qstart, self.qend)
        ireg = (self.istart, self.iend)
        return (
            f"ExtendedFileFragmentMatch: "
            f"qres: {self.qresource!r}, "
            f"ires: {self.iresource!r}, "
            f"lines={self.lines()!r}, "
            f"sc={self.score()!r}, "
            f"cov={self.coverage()!r}, "
            f"len={self.len()}, "
            f"rlen={self.rule.length}, "
            f"qreg={qreg!r}, "
            f"ireg={ireg!r}"
            f"qspan={self.qspan}"
            f"ispan={self.ispan}"
        )

    # NOTE: we implement all rich comparison operators with some inlining for performance reasons,
    # and we ignore the qresource side. We never compare matches for different resources.

    def __eq__(self, other):
        """
        Strict equality is based on matched resource and matched positions.
        """
        return (
            isinstance(other, ExtendedFileFragmentMatch)
            and self.qspan == other.qspan
            and self.ispan == other.ispan
            and self.iresource == other.iresource
        )

    def __ne__(self, other):
        """
        Strict inequality is based on matched resource and matched positions.
        """
        return (
            not isinstance(other, ExtendedFileFragmentMatch)
            or self.qspan != other.qspan
            or self.ispan != other.ispan
            or self.iresource != other.iresource
        )

    def __lt__(self, other):
        if not isinstance(other, ExtendedFileFragmentMatch):
            return NotImplemented

        return self.qstart < other.qstart

    def __lte__(self, other):
        if not isinstance(other, ExtendedFileFragmentMatch):
            return NotImplemented

        return self.qstart < other.qstart or (
            self.qspan == other.qspan
            and self.ispan == other.ispan
            and self.iresource == other.iresource
        )

    def __gt__(self, other):
        if not isinstance(other, ExtendedFileFragmentMatch):
            return NotImplemented

        return self.qstart > other.qstart

    def __gte__(self, other):
        if not isinstance(other, ExtendedFileFragmentMatch):
            return NotImplemented

        return self.qstart > other.qstart or (
            self.qspan == other.qspan
            and self.ispan == other.ispan
            and self.iresource == other.iresource
        )

    def lines(self, line_by_pos=None):
        if line_by_pos:
            self.set_lines(line_by_pos)
        return self.start_line, self.end_line

    def set_lines(self, line_by_pos):
        """
        Set this match start and end lines using a mapping of ``line_by_pos`` {pos: line}.
        """
        self.start_line = line_by_pos[self.qstart]
        self.end_line = line_by_pos[self.qend]

    @property
    def qstart(self):
        return self.qspan.start

    @property
    def qend(self):
        return self.qspan.end

    def len(self):
        """
        Return the length of the match as the number of matched query tokens.
        """
        return len(self.qspan)

    @property
    def istart(self):
        return self.ispan.start

    @property
    def iend(self):
        return self.ispan.end

    def __contains__(self, other):
        """
        Return True if qspan contains other.qspan and ispan contains other.ispan.
        """
        return other.qspan in self.qspan and other.ispan in self.ispan

    def qcontains(self, other):
        """
        Return True if qspan contains other.qspan.
        """
        return other.qspan in self.qspan

    def qdistance_to(self, other):
        """
        Return the absolute qspan distance to other match.
        Overlapping matches have a zero distance.
        Non-overlapping touching matches have a distance of one.
        """
        return self.qspan.distance_to(other.qspan)

    def idistance_to(self, other):
        """
        Return the absolute ispan distance from self to other match.
        Overlapping matches have a zero distance.
        Non-overlapping touching matches have a distance of one.
        """
        return self.ispan.distance_to(other.ispan)

    def overlap(self, other):
        """
        Return the number of overlapping positions with other.
        """
        return self.qspan.overlap(other.qspan)

    def _icoverage(self):
        """
        Return the coverage of this match to the matched rule as a float between
        0 and 1.
        """
        if not self.rule.length:
            return 0
        return self.len() / self.rule.length

    def coverage(self):
        """
        Return the coverage of this match to the matched index Resource as a rounded float
        between 0 and 100.
        """
        return round(self._icoverage() * 100, 2)

    def qmagnitude(self):
        """
        Return the maximal query length represented by this match start and end in the query
        Resource. This number represents the full extent of the matched query region.

        If the match is a contiguous match without any gaps in its range:
        - Then the magnitude is the same as the length of the match

        If the match is not a contiguous match with gaps in its range:
        - Then the magnitude will be greater than the matched length accounting for the gaps.
        match with gaps between its matched tokens.
        """
        # The query side of the match may not be contiguous. Therefore we need to compute the real
        # portion query length including alltokens that is included in this match, for both matched
        # and unmatched tokens.

        query = self.query
        qspan = self.qspan
        qmagnitude = self.qregion_len()

        # Compute a count of unknown tokens that are inside the matched
        # range, ignoring end position of the query span: unknowns here do
        # not matter as they are never in the match but they influence the
        # score.
        unknowns_pos = qspan & query.unknowns_span
        qspe = qspan.end
        unknowns_pos = (pos for pos in unknowns_pos if pos != qspe)
        qry_unkxpos = query.unknowns_by_pos
        unknowns_in_match = sum(qry_unkxpos[pos] for pos in unknowns_pos)

        # update the magnitude by adding the count of unknowns in the match.
        # This number represents the full extent of the matched query region
        # including matched, unmatched and unknown tokens.
        qmagnitude += unknowns_in_match

        return qmagnitude

    def is_continuous(self):
        """
        Return True if the all the matched tokens of this match are continuous
        without any extra unmatched known or unkwown words, or stopwords.
        """
        return self.len() == self.qregion_len() == self.qmagnitude()

    def qregion(self):
        """
        Return the maximal positions Span representing this match from
        start to end as query positions, including matched and unmatched tokens.
        """
        return Span(self.qstart, self.qend)

    def qregion_len(self):
        """
        Return the maximal number of positions represented by this match start
        and end region of query positions including matched and unmatched
        tokens.
        """
        return self.qspan.magnitude()

    def qregion_lines(self):
        """
        Return the maximal lines Span that this match query regions covers.
        """
        return Span(self.start_line, self.end_line)

    def qregion_lines_len(self):
        """
        Return the maximal number of lines that this match query regions covers.
        """
        return self.end_line - self.start_line + 1

    def qdensity(self):
        """
        Return the query density of this match as a ratio of its length to its qmagnitude, a float
        between 0 and 1. A dense match has all its matched query tokens contiguous and a maximum
        qdensity of one. A sparse low qdensity match has some non-contiguous matched query tokens
        interspersed between matched query tokens. An empty match has a zero qdensity.
        """
        mlen = self.len()
        if not mlen:
            return 0
        qmagnitude = self.qmagnitude()
        if not qmagnitude:
            return 0
        return mlen / qmagnitude

    def idensity(self):
        """
        Return the ispan density of this match as a ratio of its rule-side matched length to its
        rule side magnitude. This is a float between 0 and 1. A dense match has all its matched rule
        tokens contiguous and a maximum idensity of one. A sparse low idensity match has some non-
        contiguous matched rule tokens interspersed between matched rule tokens. An empty match has
        a zero qdensity.
        """
        return self.ispan.density()

    def score(self):
        """
        Return the score for this match as a rounded float between 0 and 100.

        The score is an indication of the confidence that a match is good. It is computed from the
        number of matched tokens, the number of query tokens in the matched range (including
        unknowns and unmatched) and the matched rule relevance.
        """
        qmagnitude = self.qmagnitude()

        # Compute the score as the ration of the matched query length to the
        # qmagnitude, e.g. the length of the matched region
        if not qmagnitude:
            return 0

        # FIXME: this should exposed as an q/icoverage() method instead
        query_coverage = self.len() / qmagnitude
        index_coverage = self._icoverage()
        if query_coverage < 1 and index_coverage < 1:
            # use coverage in this case
            return round(index_coverage * 100, 2)
        return round(query_coverage * index_coverage * 100, 2)

    def surround(self, other):
        """
        Return True if this match query span surrounds other other match query
        span.

        This is different from containment. A matched query region can surround
        another matched query region and have no positions in common with the
        surrounded match.
        """
        return self.qstart <= other.qstart and self.qend >= other.qend

    def is_after(self, other):
        """Return True if this match spans are strictly after other match spans."""
        return self.qspan.is_after(other.qspan) and self.ispan.is_after(other.ispan)

    def combine(self, other):
        """Return a new match object combining self and an other match."""
        if self.rule != other.rule:
            raise TypeError(
                "Cannot combine matches with different rules: "
                f"from: {self!r}, to: {other!r}"
            )

        if other.matcher not in self.matcher:
            newmatcher = " ".join([self.matcher, other.matcher])
            newmatcher_order = max([self.matcher_order, other.matcher_order])
        else:
            newmatcher = self.matcher
            newmatcher_order = self.matcher_order

        combined = ExtendedFileFragmentMatch(
            rule=self.rule,
            qspan=Span(self.qspan | other.qspan),
            ispan=Span(self.ispan | other.ispan),
            hispan=Span(self.hispan | other.hispan),
            query_run_start=min(self.query_run_start, other.query_run_start),
            matcher=newmatcher,
            matcher_order=newmatcher_order,
            query=self.query,
        )
        return combined

    def update(self, other):
        """Update self with other match and return the updated self in place."""
        combined = self.combine(other)
        self.qspan = combined.qspan
        self.ispan = combined.ispan
        return self

    def itokens(self, idx):
        """Return the sequence of matched itoken ids."""
        ispan = self.ispan
        rid = self.rule.rid
        if rid is not None:
            for pos, token in enumerate(idx.tids_by_rid[rid]):
                if pos in ispan:
                    yield token
