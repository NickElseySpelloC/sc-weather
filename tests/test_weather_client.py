from __future__ import annotations

from datetime import UTC, datetime

from sc_weather import WeatherClient
from sc_weather.models import (
    AstralInfo,
    SkyCondition,
    Temperature,
    WeatherCondition,
    WeatherData,
    WeatherDisplayInfo,
    WeatherReading,
    WeatherStation,
    Wind,
)
from sc_weather.providers.open_meteo_provider import OpenMeteoProvider
from sc_weather.providers.owm_provider import OWMProvider


def _sample_weather_data(source: str) -> WeatherData:
    utc_time = datetime(2025, 12, 20, 12, 0, tzinfo=UTC)
    local_time = utc_time.astimezone()
    return WeatherData(
        current=WeatherReading(
            utc_time=utc_time,
            local_time=local_time,
            temperature=Temperature(reading=22.0, feels_like=21.0),
            sky=SkyCondition(
                title="Clear",
                description="Clear sky",
                icon_info=WeatherDisplayInfo(
                    wmo_code=0,
                    condition_key=WeatherCondition.CLEAR,
                    day_night_variant="day",
                    icon_name="clear-day",
                    unicode_char="☀️",
                ),
            ),
            wind=Wind(speed=12.0, deg=180.0, direction="S"),
            astral_info=AstralInfo(
                sunrise=local_time.replace(hour=6),
                sunset=local_time.replace(hour=18),
                sunrise_icon_name="sunrise",
                sunrise_unicode_char="🌅",
                sunset_icon_name="sunset",
                sunset_unicode_char="🌇",
            ),
            precipitation_icon_name="raindrop",
            precipitation_unicode_char="💧",
            wind_icon_name="windsock",
            wind_unicode_char="💨",
            summary="Clear sky",
        ),
        hourly=[],
        daily=[],
        station=WeatherStation(source=source, latitude=-33.86, longitude=151.21),
        as_at=local_time,
    )


def test_client_falls_back_to_open_meteo(mocker):
    expected = _sample_weather_data("Open-Meteo")

    mocker.patch.object(OWMProvider, "fetch", side_effect=RuntimeError("boom"))
    open_meteo_fetch = mocker.patch.object(OpenMeteoProvider, "fetch", return_value=expected)

    client = WeatherClient(-33.86, 151.21, owm_api_key="dummy")
    assert client.get_weather() == expected
    open_meteo_fetch.assert_called_once()


def test_client_uses_owm_when_available(mocker):
    expected = _sample_weather_data("OpenWeatherMap One Call API")

    owm_fetch = mocker.patch.object(OWMProvider, "fetch", return_value=expected)
    mocker.patch.object(OpenMeteoProvider, "fetch", side_effect=AssertionError("should not call"))

    client = WeatherClient(-33.86, 151.21, owm_api_key="dummy")
    assert client.get_weather() == expected
    owm_fetch.assert_called_once()


def test_client_uses_requested_icon_library():
    client = WeatherClient(-33.86, 151.21, icon_library="weather-icons")

    assert client._icon_provider.library == "weather-icons"  # noqa: SLF001
    assert client._icon_provider.theme == "monochrome-black-static"  # noqa: SLF001
