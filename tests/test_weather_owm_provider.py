from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pyowm.commons.exceptions import UnauthorizedError
from requests import HTTPError

from sc_weather.icon_provider import WeatherIconProvider
from sc_weather.providers.owm_provider import OWMProvider


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = type("Response", (), {"status_code": self.status_code})()
            error_msg = f"HTTP {self.status_code} Error"
            raise HTTPError(error_msg, response=response)  # pyright: ignore[reportArgumentType]

    def json(self):
        return self._payload


def test_owm_provider_falls_back_to_free_endpoints_on_unauthorized(mocker):
    provider = OWMProvider("dummy", WeatherIconProvider())
    base_now = datetime.now(tz=UTC)
    local_now = base_now.astimezone()
    mocker.patch.object(
        provider._mgr,  # noqa: SLF001
        "one_call",
        side_effect=UnauthorizedError("Invalid API Key provided"),
    )
    mocker.patch(
        "sc_weather.providers.owm_provider.DateHelper.get_dawn_dusk_times",
        return_value={
            "sunrise": local_now.replace(hour=6, minute=0, second=0, microsecond=0),
            "sunset": local_now.replace(hour=18, minute=0, second=0, microsecond=0),
        },
    )

    current_payload = {
        "main": {"temp": 20.5, "temp_max": 21.0, "temp_min": 19.0, "feels_like": 20.0, "pressure": 1012, "humidity": 55},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "wind": {"speed": 3.2, "deg": 180},
        "clouds": {"all": 0},
        "visibility": 10000,
    }

    forecast_payload = {
        "list": [
            {
                "dt": int(base_now.timestamp()) + 3 * 3600,
                "main": {"temp": 21.0, "temp_max": 22.0, "temp_min": 20.0, "feels_like": 21.0, "pressure": 1010, "humidity": 50},
                "weather": [{"id": 801, "main": "Clouds", "description": "few clouds", "icon": "02d"}],
                "wind": {"speed": 2.8, "deg": 170},
                "clouds": {"all": 25},
                "visibility": 10000,
                "pop": 0.2,
            }
        ]
    }

    get = mocker.patch(
        "sc_weather.providers.owm_provider.requests.get",
        side_effect=[
            _FakeResponse(current_payload),
            _FakeResponse(forecast_payload),
        ],
    )

    weather = provider.fetch(-33.86, 151.21)

    assert weather.station.source == "OpenWeatherMap Free API"
    assert weather.current.temperature.reading == 20.5
    assert weather.current.sky.icon_info.wmo_code == 0
    # assert weather.current.sky.icon_info.icon_name == "clear-day"
    assert weather.current.astral_info.sunrise_icon_name == "sunrise"
    assert weather.current.precipitation_icon_name == "raindrop"
    assert weather.hourly
    assert weather.hourly[0].temperature.reading == 21.0
    assert weather.hourly[0].sky.icon_info.wmo_code == 1
    assert get.call_count == 2


def test_owm_provider_free_endpoint_http_error_raises(mocker):
    provider = OWMProvider("dummy", WeatherIconProvider())
    mocker.patch.object(provider._mgr, "one_call", side_effect=UnauthorizedError("nope"))  # noqa: SLF001
    mocker.patch(
        "sc_weather.providers.owm_provider.requests.get",
        return_value=_FakeResponse({}, status_code=401),
    )

    with pytest.raises(RuntimeError):
        provider.fetch(-33.86, 151.21)
