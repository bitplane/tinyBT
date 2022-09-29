"""
The MIT License

Copyright (c) 2014 Fred Stober

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

import socket
import struct
from typing import Tuple

client_version = (b"XK", 0, 0x01)  # eXperimental Klient 0.0.1


def encode_ip(ip_address: str) -> bytes:
    return socket.inet_aton(ip_address)


def encode_uint16(value: int) -> bytes:
    return struct.pack("!H", value)


def encode_uint32(value: int) -> bytes:
    return struct.pack("!I", value)


def encode_uint64(value: int) -> bytes:
    return struct.pack("!Q", value)


def encode_int32(value: int) -> bytes:
    return struct.pack("!i", value)


def encode_connection(con) -> bytes:
    return encode_ip(con[0]) + encode_uint16(con[1])


def encode_nodes(nodes) -> bytes:
    result = b""
    for node in nodes:
        result += bytes(bytearray(node.id).rjust(20, b"\0")) + encode_connection(
            node.connection
        )
    return result


def decode_ip(ip_4_bytes: bytes) -> str:
    return socket.inet_ntoa(ip_4_bytes)


def decode_uint16(value: bytes) -> str:
    return struct.unpack("!H", value)[0]


def decode_uint32(value: bytes) -> str:
    return struct.unpack("!I", value)[0]


def decode_uint64(value: bytes) -> str:
    return struct.unpack("!Q", value)[0]


def decode_connection(con: bytes) -> Tuple[bytes, int]:
    return (decode_ip(con[0:4]), decode_uint16(con[4:6]))


def decode_nodes(nodes: bytes):
    try:
        while nodes:
            node_id = struct.unpack("20s", nodes[:20])[0]
            node_connection = decode_connection(nodes[20:26])
            if node_connection[1] >= 1024:  # discard invalid port numbers
                yield (node_id, node_connection)
            nodes = nodes[26:]
    except Exception:
        pass  # catch malformed nodes


def decode_connections(data: bytes):
    while len(data) >= 6:
        c = decode_connection(data[0:6])
        if c[1] >= 1024:
            yield c
        data = data[6:]


def decode_id(node_id: bytes) -> int:
    return int.from_bytes(node_id, byteorder="big")
