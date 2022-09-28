from pytest import raises

from tinybt.utils.bencode import BTFailure, bdecode


def test_empty_dict():
    assert bdecode(b"de") == {}


def test_string():
    assert bdecode(b"0:").decode() == ""
    assert bdecode(b"4:test").decode() == "test"
    assert bdecode(b"13:longer string").decode() == "longer string"

    utf_test = b"16:\xf0\x9f\x86\x83\xf0\x9f\x85\xb4\xf0\x9f\x86\x82\xf0\x9f\x86\x83"
    assert bdecode(utf_test).decode() == "🆃🅴🆂🆃"


def test_empty_list():
    assert bdecode(b"le") == []


def test_int():
    assert bdecode(b"i1e") == 1
    assert bdecode(b"i-1e") == -1
    assert bdecode(b"i12345e") == 12345


def test_bytes():
    assert bdecode(b"0:") == b""
    assert bdecode(b"4:\0\0\0\0") == b"\0\0\0\0"


def test_nested():
    assert bdecode(b"l1:b1:al1:cdi0eli1e1:deeee") == [
        b"b",
        b"a",
        [b"c", {0: [1, b"d"]}],
    ]


def test_invalid():
    with raises(BTFailure):
        bdecode(b"qqq not valid bencoded data")


def test_extra_data():
    with raises(BTFailure):
        bdecode(b"4:too long")


def test_truncated():
    with raises(BTFailure):
        bdecode(b"4000:nelly the elephant packed her trunk wrong")


def test_bad_type():
    with raises(BTFailure):
        bdecode(b"i^e")
