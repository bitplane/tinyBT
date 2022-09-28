from tinybt.utils.bencode import bencode


def test_empty_dict():
    assert bencode({}) == b"de"


def test_string():
    assert bencode("") == b"0:"
    assert bencode("test") == b"4:test"
    assert bencode("longer string") == b"13:longer string"
    assert (
        bencode("🆃🅴🆂🆃")
        == b"16:\xf0\x9f\x86\x83\xf0\x9f\x85\xb4\xf0\x9f\x86\x82\xf0\x9f\x86\x83"
    )


def test_empty_list():
    assert bencode([]) == b"le"


def test_int():
    assert bencode(1) == b"i1e"
    assert bencode(-1) == b"i-1e"
    assert bencode(12345) == b"i12345e"


def test_bytes():
    assert bencode(b"") == b"0:"
    assert bencode(b"\0\0\0\0") == b"4:\0\0\0\0"


def test_sort_dict():
    unsorted = {"c": 3, "a": 1, "b": 2}
    assert bencode(unsorted) == b"d1:ai1e1:bi2e1:ci3ee"


def test_nested():
    mixed = ["b", "a", ["c", {0: [1, "d"]}]]
    assert bencode(mixed) == b"l1:b1:al1:cdi0eli1e1:deeee"
