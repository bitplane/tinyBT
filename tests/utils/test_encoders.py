from tinybt.utils import (
    encode_connection,
    encode_int32,
    encode_ip,
    encode_uint16,
    encode_uint32,
    encode_uint64,
)


def test_encode_ip():
    assert encode_ip("127.0.2.1") == b"\x7f\x00\x02\x01"


def test_encode_uint16():
    assert encode_uint16(65535) == b"\xff\xff"
    assert encode_uint16(1234) == b"\x04\xd2"


def test_encode_uint32():
    assert encode_uint32(65536) == b"\x00\x01\x00\x00"
    assert encode_uint32(4294967295) == b"\xff\xff\xff\xff"


def test_encode_uint64():
    assert encode_uint64(0) == b"\0\0\0\0\0\0\0\0"
    assert encode_uint64(1234567890) == b"\x00\x00\x00\x00I\x96\x02\xd2"


def test_encode_int32():
    assert encode_int32(-1) == b"\xff\xff\xff\xff"


def test_encode_connection():
    con = ("111.122.133.144", 5900)
    assert encode_connection(con) == b"oz\x85\x90\x17\x0c"


# def test_encode_nodes():
#    raise NotImplementedError()
