import pytest

from sesdev import _parse_roles


def test_pytest_parse_roles():
    assert _parse_roles('[master]') == [["master"]], "test failed"
    assert _parse_roles('[[master]]') == [["master"]], "test failed"
    assert _parse_roles('[foo]') == [["foo"]], "test failed"
    assert _parse_roles('[[foo]]') == [["foo"]], "test failed"
    assert _parse_roles('[[foo],  []]') == [["foo"], []], "test failed"
    assert _parse_roles('  [    [ ],[foo],  []]') == [[], ["foo"], []], "test failed"
    assert _parse_roles("""
      [ ],
  [foo],
  []
""") == [[], ["foo"], []], "test failed"
    assert _parse_roles('[bootstrap, fortel, client],[client]') == \
        [["bootstrap", "client", "fortel"], ["client"]], "test failed"
