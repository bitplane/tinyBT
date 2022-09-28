from tinybt.utils import (
    decode_connection,
    decode_ip,
    decode_uint16,
    decode_uint32,
    decode_uint64,
)


def test_decode_ip():
    assert decode_ip(b"\x7f\x00\x02\x01") == "127.0.2.1"


def test_decode_uint16():
    assert decode_uint16(b"\xff\xff") == 65535
    assert decode_uint16(b"\xf0\x00") == 61440


def test_decode_uint32():
    assert decode_uint32(b"\xff\xff\xff\xff") == 2**32 - 1
    assert decode_uint32(b"\xba\xdf\x00\x0d") == 0xBADF000D


def test_decode_uint64():
    assert decode_uint64(b"\xff\xff\xff\xff\xff\xff\xff\xff") == 2**64 - 1
    assert decode_uint64(b"\xde\xad\xbe\xef\xba\xdf\x00\x0d") == 0xDEADBEEFBADF000D


def test_decode_connection():
    con = b"oz\x85\x90\x17\x0c"
    assert decode_connection(con) == ("111.122.133.144", 5900)


# def test_decode_nodes(nodes):
#    raise NotImplementedError()
