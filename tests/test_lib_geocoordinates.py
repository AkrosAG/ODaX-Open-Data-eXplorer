from typing import Any
import numpy as np
import pandas as pd
import pytest

# ⬇️ change this import to your actual module path/file name
from imping.nabel_airquality.lib_geocoordinates import (
    swiss_lv95_to_wgs84,
    parse_coords,
    get_wgs84_municipality,
    idw_interpolate,
)

# ---------------------------
# Helpers for mocking requests
# ---------------------------


class _FakeResponse:
    def __init__(
        self, *, status_code=200, json_data: Any = None, raise_for_status_exc=None
    ):
        self.status_code = status_code
        self._json_data = json_data
        self._raise_for_status_exc = raise_for_status_exc

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data

    def raise_for_status(self):
        if self._raise_for_status_exc:
            raise self._raise_for_status_exc


# ---------------------------
# swiss_lv95_to_wgs84
# ---------------------------


def test_swiss_lv95_to_wgs84_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        # function returns (lon, lat) according to your code: data["easting"], data["northing"]
        return _FakeResponse(json_data={"easting": 7.44, "northing": 46.95})

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    lon, lat = swiss_lv95_to_wgs84(2600000, 1200000)
    assert lon == pytest.approx(7.44)
    assert lat == pytest.approx(46.95)


def test_swiss_lv95_to_wgs84_error(monkeypatch, capsys):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(raise_for_status_exc=RuntimeError("boom"))

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    lon, lat = swiss_lv95_to_wgs84(0, 0)
    assert lon is None and lat is None
    # optional: check error message printed
    assert "Conversion failed" in capsys.readouterr().out


# ---------------------------
# parse_coords
# ---------------------------


@pytest.mark.parametrize(
    "east, north, expected",
    [
        (2600000, 1200000, (2600000.0, 1200000.0)),  # numeric inputs
        ("2600000", "1200000", (2600000.0, 1200000.0)),  # numeric strings
        ("2600000/1200000", None, (2600000.0, 1200000.0)),  # split format
    ],
)
def test_parse_coords_valid(east, north, expected):
    assert parse_coords(east, north) == expected


@pytest.mark.parametrize(
    "east, north",
    [
        ("not-a-number", "1200000"),
        ("2600000/notanumber", None),
        (2600000, None),  # second missing and not splittable
    ],
)
def test_parse_coords_invalid(east, north):
    assert parse_coords(east, north) == (None, None)


# ---------------------------
# get_wgs84_municipality
# ---------------------------


def test_get_wgs84_municipality_found(monkeypatch):
    # Mock a response with list of results; pick the first having featureId
    payload = {
        "results": [
            {"attrs": {"featureId": None}},  # should be skipped
            {
                "attrs": {"featureId": 123, "lat": "46.948", "lon": "7.447"}
            },  # Bern, e.g.
        ]
    }

    def fake_get(url, params=None):
        return _FakeResponse(json_data=payload)

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    coords = get_wgs84_municipality("Bern")
    assert coords == (pytest.approx(46.948), pytest.approx(7.447))


def test_get_wgs84_municipality_not_found(monkeypatch):
    payload = {"results": [{"attrs": {"featureId": None}}]}  # nothing usable

    def fake_get(url, params=None):
        return _FakeResponse(json_data=payload)

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    assert get_wgs84_municipality("Nowhere") is None


def test_get_wgs84_municipality_error(monkeypatch, capsys):
    def fake_get(url, params=None):
        return _FakeResponse(raise_for_status_exc=RuntimeError("bad request"))

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    assert get_wgs84_municipality("Bern") is None
    assert "Municipality lookup failed" in capsys.readouterr().out


# ---------------------------
# idw_interpolate
# ---------------------------


def test_idw_interpolate_exact_match():
    df = pd.DataFrame(
        {
            "WGS84_Latitude": [46.0, 46.5],
            "WGS84_Longitude": [7.0, 7.5],
            "value": [10.0, 20.0],
        }
    )
    # target equals first station → should return its value exactly
    out = idw_interpolate(df, target_lat=46.0, target_lon=7.0, value_col="value")
    assert out == 10.0


def test_idw_interpolate_basic_average():
    # symmetric points around target (very close), should be average-ish with power=2
    df = pd.DataFrame(
        {
            "WGS84_Latitude": [0.0, 0.0],
            "WGS84_Longitude": [-1.0, 1.0],
            "value": [10.0, 30.0],
        }
    )
    out = idw_interpolate(
        df, target_lat=0.0, target_lon=0.0, value_col="value", k=2, power=2
    )
    # equal distance → equal weights → average = 20
    assert out == pytest.approx(20.0, abs=1e-6)


def test_idw_interpolate_handles_nan_and_k_gt_n():
    df = pd.DataFrame(
        {
            "WGS84_Latitude": [0.0, 0.1, 0.2],
            "WGS84_Longitude": [0.0, 0.0, 0.0],
            "value": [np.nan, 40.0, 80.0],
        }
    )
    # avoid exact match to the NaN station
    out = idw_interpolate(df, 0.00001, 0.0, value_col="value", k=10, power=2)
    assert 40.0 <= out <= 80.0


def test_idw_interpolate_all_nan_returns_nan():
    df = pd.DataFrame(
        {
            "WGS84_Latitude": [0.0, 0.1],
            "WGS84_Longitude": [0.0, 0.1],
            "value": [np.nan, np.nan],
        }
    )
    out = idw_interpolate(df, 0.0, 0.0, value_col="value", k=2, power=2)
    assert np.isnan(out)
