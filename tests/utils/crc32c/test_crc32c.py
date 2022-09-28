from tinybt.utils.crc32c import crc32c


def test_empty():
    assert crc32c(bytearray(b"")) == 0


def test_some_bytes():
    assert crc32c(bytearray(b"some bytes")) == 4140651843
