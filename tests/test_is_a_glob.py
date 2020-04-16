import pytest

from sesdev import _is_a_glob

def test_pytest_is_a_glob():
    assert _is_a_glob("*"), "test failed"
    assert _is_a_glob("foo*"), "test failed"
    assert _is_a_glob("node[123]"), "test failed"
    assert _is_a_glob("{foo,bar}"), "test failed"
    assert not _is_a_glob("bamboozle"), "test failed"
    assert _is_a_glob("node?"), "test failed"
