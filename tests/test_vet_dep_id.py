import pytest

from seslib.deployment import _vet_dep_id
from seslib.exceptions import DepIDWrongLength, DepIDIllegalChars


def test_vet_dep_id():
    assert _vet_dep_id("hooholopar") == "hooholopar"
    assert _vet_dep_id("oron1anio0") == "oron1anio0"
    assert _vet_dep_id("hyphen-words-separated") == "hyphen-words-separated"
    with pytest.raises(DepIDWrongLength):
        _vet_dep_id("")
    with pytest.raises(DepIDWrongLength):
        long_string = (
            "hooholoparhooholoparhooholoparhooholoparhooh"
            "hooholoparhooholoparhooholoparhooholoparhooh"
            "hooholoparhooholoparhooholoparhooholoparhooh"
            "hooholoparhooholoparhooholoparhooholoparhooh"
        )
        _vet_dep_id(long_string)
    with pytest.raises(DepIDIllegalChars):
        _vet_dep_id("hooholopar;")
    with pytest.raises(DepIDIllegalChars):
        _vet_dep_id("master]")
    with pytest.raises(DepIDIllegalChars):
        _vet_dep_id("master_id")
