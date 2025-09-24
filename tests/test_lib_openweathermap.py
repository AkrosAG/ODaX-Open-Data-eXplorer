from unittest.mock import patch, MagicMock, ANY
import sys
import os

# Add the parent directory to sys.path to import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ✅ update this import path if your module lives elsewhere
from deployment.postgres.script.imping.nabel_airquality.lib_openweathermap import get_air_quality


def test_get_air_quality_success():
    lat, lon, key = 46.948, 7.447, "TEST_KEY"
    fake_payload = {
        "coord": {"lon": lon, "lat": lat},
        "list": [
            {
                "main": {"aqi": 2},
                "components": {
                    "co": 201.94,
                    "no": 0.0,
                    "no2": 0.77,
                    "o3": 68.66,
                    "so2": 0.64,
                    "pm2_5": 3.01,
                    "pm10": 4.12,
                    "nh3": 0.12,
                },
                "dt": 1730846400,
            }
        ],
    }

    with patch("deployment.postgres.script.imping.nabel_airquality.lib_openweathermap.requests.get") as mock_get:
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = fake_payload
        mock_get.return_value = resp

        data = get_air_quality(lat, lon, key)

        expected_url = (
            f"https://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={lat}&lon={lon}&appid={key}"
        )
        mock_get.assert_called_once_with(expected_url, timeout=ANY)

        assert data is fake_payload
        assert data["coord"] == {"lon": lon, "lat": lat}
        assert data["list"][0]["main"]["aqi"] == 2


def test_get_air_quality_http_error_returns_none():
    lat, lon, key = 46.0, 7.0, "TEST_KEY"

    with patch("deployment.postgres.script.imping.nabel_airquality.lib_openweathermap.requests.get") as mock_get:
        resp = MagicMock()
        from requests.exceptions import HTTPError

        resp.raise_for_status.side_effect = HTTPError("Bad Request")
        mock_get.return_value = resp

        result = get_air_quality(lat, lon, key)
        assert result is None


def test_get_air_quality_request_exception_returns_none():
    lat, lon, key = 0.0, 0.0, "KEY"

    from requests.exceptions import RequestException

    with patch("deployment.postgres.script.imping.nabel_airquality.lib_openweathermap.requests.get") as mock_get:
        mock_get.side_effect = RequestException("network is down")

        result = get_air_quality(lat, lon, key)
        assert result is None
