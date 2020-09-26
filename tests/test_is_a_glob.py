import pytest

from seslib.tools import is_a_glob


def test_pytestis_a_glob():
    assert is_a_glob("*"), "test failed"
    assert is_a_glob("foo*"), "test failed"
    assert is_a_glob("node[123]"), "test failed"
    assert is_a_glob("{foo,bar}"), "test failed"
    assert not is_a_glob("bamboozle"), "test failed"
    assert is_a_glob("node?"), "test failed"
