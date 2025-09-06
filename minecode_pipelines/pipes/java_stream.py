# The MIT License (MIT)
#
# Copyright (c) 2014 Gustav Arngården
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Reading from Java DataInputStream format."""

import struct


class DataInputStream:
    def __init__(self, stream):
        self.stream = stream

    def read(self, n=1):
        data = self.stream.read(n)
        if len(data) != n:
            # this is a problem but in most cases we have reached EOF
            raise EOFError
        return data

    def read_byte(self):
        return struct.unpack("b", self.read(1))[0]

    def read_long(self):
        return struct.unpack(">q", self.read(8))[0]

    def read_utf(self):
        utf_length = struct.unpack(">H", self.read(2))[0]
        return self.read(utf_length)

    def read_int(self):
        return struct.unpack(">i", self.read(4))[0]
