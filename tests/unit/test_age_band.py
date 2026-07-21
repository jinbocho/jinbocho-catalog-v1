from datetime import datetime

from app.application.services import age_band_for_birth_year


def test_none_birth_year_returns_none() -> None:
    assert age_band_for_birth_year(None) is None


def test_bands_by_age() -> None:
    today = datetime(2026, 1, 1)
    assert age_band_for_birth_year(2023, today) == "shared"
    assert age_band_for_birth_year(2019, today) == "emerging"
    assert age_band_for_birth_year(2015, today) == "fluent"
    assert age_band_for_birth_year(2010, today) == "teen"


def test_band_boundaries() -> None:
    today = datetime(2026, 1, 1)
    assert age_band_for_birth_year(2021, today) == "shared"
    assert age_band_for_birth_year(2020, today) == "emerging"
    assert age_band_for_birth_year(2018, today) == "emerging"
    assert age_band_for_birth_year(2017, today) == "fluent"
    assert age_band_for_birth_year(2014, today) == "fluent"
    assert age_band_for_birth_year(2013, today) == "teen"
