#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import binascii

from matchcode_toolkit.halohash import BitAverageHaloHash


def _create_directory_fingerprint(inputs):
    """
    Return a 128-bit BitAverageHaloHash fingerprint in hex from `inputs`
    """
    inputs = [i.encode('utf-8') for i in inputs if i]
    bah128 = BitAverageHaloHash(inputs, size_in_bits=128).hexdigest()
    inputs_count = len(inputs)
    inputs_count_hex_str = '%08x' % inputs_count
    bah128 = bah128.decode('utf-8')
    directory_fingerprint = inputs_count_hex_str + bah128
    return directory_fingerprint


def create_content_fingerprint(resources):
    """
    Collect SHA1 strings from a list of Resources (`resources`) and create a
    directory fingerprint from them
    """
    features = [r.sha1 for r in resources if r.sha1]
    return _create_directory_fingerprint(features)


def _get_resource_subpath(resource, top):
    """
    Return the subpath of `resource` relative to `top` from `codebase`

    For example:

    top.path = 'foo/bar/'
    resource.path = 'foo/bar/baz.c'

    The subpath returned would be 'baz.c'
    """
    _, _, subpath = resource.path.partition(top.path)
    subpath = subpath.lstrip('/')
    return subpath


def create_structure_fingerprint(directory, children):
    """
    Collect the subpaths of children Resources of Resource `directory` and
    create a fingerprint from them
    """
    features = []
    for child in children:
        if not child.path:
            continue
        child_subpath = _get_resource_subpath(child, directory)
        if not child.size:
            rounded_child_size = 0
        else:
            rounded_child_size = int(child.size / 10) * 10
        path_feature = str(rounded_child_size) + child_subpath
        features.append(path_feature)
    return _create_directory_fingerprint(features)


def compute_directory_fingerprints(codebase):
    """
    Compute fingerprints for a directory from `codebase`
    """
    for resource in codebase.walk(topdown=False):
        if resource.is_file or not resource.path:
            continue
        children = [r for r in resource.walk(codebase) if r.is_file]
        if len(children) == 1:
            continue
        resource.extra_data['directory_content'] = create_content_fingerprint(children)
        resource.extra_data['directory_structure'] = create_structure_fingerprint(resource, children)
        resource.save(codebase)
    return codebase


def split_fingerprint(directory_fingerprint):
    """
    Given a string `directory_fingerprint`, return the indexed elements count as
    an integer and the bah128 fingerprint string
    """
    indexed_elements_count_hash = directory_fingerprint[0:8]
    indexed_elements_count = int(indexed_elements_count_hash, 16)
    bah128 = directory_fingerprint[8:]
    return indexed_elements_count, bah128


def hexstring_to_binarray(hex_string):
    """
    Convert a hex string to binary form, then store in a bytearray
    """
    return bytearray(binascii.unhexlify(hex_string))


def create_halohash_chunks(bah128):
    """
    Given a 128-bit bah128 hash string, split it into 4 chunks and return those
    chunks as bytearrays
    """
    chunk1 = bah128[0:8]
    chunk2 = bah128[8:16]
    chunk3 = bah128[16:24]
    chunk4 = bah128[24:32]

    chunk1 = hexstring_to_binarray(chunk1)
    chunk2 = hexstring_to_binarray(chunk2)
    chunk3 = hexstring_to_binarray(chunk3)
    chunk4 = hexstring_to_binarray(chunk4)

    return chunk1, chunk2, chunk3, chunk4
