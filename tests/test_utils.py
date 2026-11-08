import pytest
from core.utils import parse_duration

def test_parse_duration_full():
    assert parse_duration("full") == -1
    assert parse_duration("FULL") == -1
    assert parse_duration("") == -1
    assert parse_duration(None) == -1

def test_parse_duration_seconds():
    assert parse_duration("30s") == 30
    assert parse_duration("120s") == 120

def test_parse_duration_raw_digits():
    assert parse_duration("30") == 30
    assert parse_duration("120") == 120
    assert parse_duration("3600") == 3600

def test_parse_duration_minutes():
    assert parse_duration("45m") == 45 * 60
    assert parse_duration("1m30s") == 90

def test_parse_duration_hours():
    assert parse_duration("1h") == 3600
    assert parse_duration("2h30m") == 2 * 3600 + 30 * 60
    assert parse_duration("1h30m15s") == 3600 + 1800 + 15

def test_parse_duration_invalid():
    with pytest.raises(ValueError):
        parse_duration("invalid")
        
    with pytest.raises(ValueError):
        parse_duration("1h30mX")
        
    with pytest.raises(ValueError):
        parse_duration("0s")
