import pytest
from app.slug import normalize, validate, build_device_slug

def test_normalize_slug():
    assert normalize("GE Healthcare Optima XR220") == "ge_healthcare_optima_xr220"
    assert normalize("Siêu âm Hitachi Arrietta 60") == "sieu_am_hitachi_arrietta_60"
    assert normalize("X-Quang GE") == "x_quang_ge"
    assert normalize("  Máy thở  Philips  ") == "may_tho_philips"
    assert normalize("CT-Scanner 128") == "ct_scanner_128"

def test_is_valid_slug():
    assert validate("ge_healthcare_optima_xr220") is True
    assert validate("sieu_am_123") is True
    assert validate("Invalid Slug") is False
    assert validate("slug-with-hyphen") is False
    assert validate("slug_with_123") is True
    assert validate("_invalid_start") is False
    assert validate("invalid_end_") is False

def test_build_device_slug():
    assert build_device_slug("GE", "Optima XR220") == "ge_optima_xr220"
    assert build_device_slug("Hitachi", "Arrietta 60", "Full") == "hitachi_arrietta_60_full"
