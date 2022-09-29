"""
The MIT License

Copyright (c) 2015 Fred Stober

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


class BEncodingError(Exception):
    pass


def bencode_proc(result, x):
    t = type(x)
    if t == str:
        str_bytes = x.encode()
        length = len(str_bytes)
        result.extend((str(length).encode(), b":", str_bytes))
    elif t == bytes:
        result.extend((str(len(x)).encode(), b":", x))
    elif t == int:
        result.append(f"i{x}e".encode())
    elif t == dict:
        result.append(b"d")
        for k, v in sorted(x.items()):
            bencode_proc(result, k)
            bencode_proc(result, v)
        result.append(b"e")
    elif t == list:
        result.append(b"l")
        for item in x:
            bencode_proc(result, item)
        result.append(b"e")


def bencode(x):
    result = []
    bencode_proc(result, x)
    return b"".join(result)


# Decoding functions ##############################################

bdecode_marker_int = ord("i")
bdecode_marker_str_min = ord("0")
bdecode_marker_str_max = ord("9")
bdecode_marker_list = ord("l")
bdecode_marker_dict = ord("d")
bdecode_marker_end = ord("e")


def bdecode_proc(msg, pos):
    t = msg[pos]
    if t == bdecode_marker_int:
        pos += 1
        pos_end = msg.index(b"e", pos)
        return (int(msg[pos:pos_end]), pos_end + 1)
    elif t >= bdecode_marker_str_min and t <= bdecode_marker_str_max:
        sep = msg.index(b":", pos)
        n = int(msg[pos:sep])
        sep += 1
        return (bytes(msg[sep : sep + n]), sep + n)
    elif t == bdecode_marker_dict:
        result = {}
        pos += 1
        while msg[pos] != bdecode_marker_end:
            k, pos = bdecode_proc(msg, pos)
            result[k], pos = bdecode_proc(msg, pos)
        return (result, pos + 1)
    elif t == bdecode_marker_list:
        result = []
        pos += 1
        while msg[pos] != bdecode_marker_end:
            v, pos = bdecode_proc(msg, pos)
            result.append(v)
        return (result, pos + 1)
    raise BEncodingError("invalid bencoded data (invalid token)! %r" % msg)


def bdecode_extra(msg):
    try:
        result, pos = bdecode_proc(bytearray(msg), 0)
    except (IndexError, KeyError, ValueError):
        raise BEncodingError("invalid bencoded data! %r" % msg)
    return (result, pos)


def bdecode(msg):
    result, pos = bdecode_extra(msg)

    if pos != len(msg):
        raise BEncodingError("invalid bencoded value (data after valid prefix)")
    return result
