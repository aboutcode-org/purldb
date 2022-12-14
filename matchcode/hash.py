#
# Copyright (c) nexB Inc. and others. All rights reserved.
# purldb is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/purldb for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

# From https://github.com/nexB/scancode-toolkit-contrib

import hashlib

from commoncode.codec import bin_to_num
from commoncode.codec import urlsafe_b64encode
from commoncode import filetype

"""
Hashes and checksums.

Low level hash functions using standard crypto hashes used to construct hashes
of various lengths. Hashes that are smaller than 128 bits are based on a
truncated md5. Other length use SHA hashes.

Checksums are operating on files.
"""


def _hash_mod(bitsize, hmodule):
    """
    Return a hashing class returning hashes with a `bitsize` bit length. The
    interface of this class is similar to the hash module API.
    """

    class hasher(object):

        def __init__(self, msg=None):
            self.digest_size = bitsize // 8
            self.h = msg and hmodule(msg).digest()[:self.digest_size] or None

        def digest(self):
            return self.h

        def hexdigest(self):
            return self.h and self.h.encode('hex')

        def b64digest(self):
            return self.h and urlsafe_b64encode(self.h)

        def intdigest(self):
            return self.h and bin_to_num(self.h)

    return hasher


# Base hashers for each bit size
_hashmodules_by_bitsize = {
    # md5-based
    16: _hash_mod(16, hashlib.md5),
    32: _hash_mod(32, hashlib.md5),
    64: _hash_mod(64, hashlib.md5),
    128: _hash_mod(128, hashlib.md5),
    # sha-based
    160: _hash_mod(160, hashlib.sha1),
    256: _hash_mod(256, hashlib.sha256),
    384: _hash_mod(384, hashlib.sha384),
    512: _hash_mod(512, hashlib.sha512)
}


def get_hasher(bitsize):
    """
    Return a hasher for a given size in bits of the resulting hash.
    """
    return _hashmodules_by_bitsize[bitsize]


def checksum(location, bitsize, base64=False):
    """
    Return a checksum of `bitsize` length from the content of the file at
    `location`. The checksum is a hexdigest or base64-encoded is `base64` is
    True.
    """
    if not filetype.is_file(location):
        return
    hasher = get_hasher(bitsize)

    # fixme: we should read in chunks
    with open(location, 'rb') as f:
        hashable = f.read()

    hashed = hasher(hashable)
    if base64:
        return hashed.b64digest()

    return hashed.hexdigest()


def md5(location):
    return checksum(location, bitsize=128, base64=False)


def sha1(location):
    return checksum(location, bitsize=160, base64=False)


def b64sha1(location):
    return checksum(location, bitsize=160, base64=True)


def sha256(location):
    return checksum(location, bitsize=256, base64=False)


def sha512(location):
    return checksum(location, bitsize=512, base64=False)
