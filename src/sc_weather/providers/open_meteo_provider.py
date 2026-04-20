"""WeatherClient provider for Open-Meteo weather API.

Open-Meteo is a free, open-source weather API that provides comprehensive weather data
without requiring an API key. It offers current conditions, hourly forecasts, and daily
forecasts with a wide range of meteorological variables.

Documentation: https://open-meteo.com/en/docs
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from ..icon_provider import WeatherIconProvider
from ..models import (
    SkyCondition,
    Temperature,
    WeatherData,
    WeatherReading,
    WeatherStation,
    Wind,
)
from ..normalization import (
    build_astral_info,
    is_daytime,
    wmo_code_to_title,
)


_COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


class OpenMeteoProvider:
    """Provider for Open-Meteo weather API."""

    def __init__(self, icon_provider: WeatherIconProvider):
        self._icon_provider = icon_provider

    def fetch(self, lat: float, lon: float) -> WeatherData:
        """Fetch weather data from Open-Meteo.

        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.

        Returns:
            A WeatherData object containing the current reading, hourly and daily forecasts, and weather station info.
        """
        url = self._build_api_url(lat, lon)
        data = self._fetch_api_data(url)

        local_tz = datetime.now().astimezone().tzinfo
        utc_now = datetime.now(UTC)
        time_now = datetime.now(tz=local_tz)

        daily_data = data.get("daily", {})
        daily_times = daily_data.get("time", [])
        daily_sunrise_map: dict[datetime.date, datetime | None] = {}
        daily_sunset_map: dict[datetime.date, datetime | None] = {}
        for index, date_str in enumerate(daily_times):
            date_value = datetime.fromisoformat(date_str).date()
            sunrise_str = self._get_index(daily_data.get("sunrise"), index)
            sunset_str = self._get_index(daily_data.get("sunset"), index)
            daily_sunrise_map[date_value] = datetime.fromisoformat(sunrise_str).astimezone() if sunrise_str else None
            daily_sunset_map[date_value] = datetime.fromisoformat(sunset_str).astimezone() if sunset_str else None

        current_reading = self._parse_current_weather(data, utc_now, time_now, daily_sunrise_map, daily_sunset_map)
        hourly = self._parse_hourly_forecast(data, time_now, daily_sunrise_map, daily_sunset_map)
        daily = self._parse_daily_forecast(data, time_now, daily_sunrise_map, daily_sunset_map)

        station = WeatherStation(
            source="Open-Meteo",
            latitude=data.get("latitude", lat),
            longitude=data.get("longitude", lon),
            timezone_name=data.get("timezone"),
            timezone_offset=data.get("utc_offset_seconds"),
        )

        return WeatherData(
            current=current_reading,
            hourly=hourly,
            daily=daily,
            station=station,
            as_at=datetime.now(tz=local_tz),
        )

    @staticmethod
    def _build_api_url(lat: float, lon: float) -> str:
        """Build the Open-Meteo API URL with all required parameters.

        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.

        Returns:
            str: The complete API URL.
        """
        current_params = [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "weather_code",
            "cloud_cover",
            "pressure_msl",
            "surface_pressure",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ]

        hourly_params = [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation_probability",
            "precipitation",
            "rain",
            "weather_code",
            "pressure_msl",
            "cloud_cover",
            "visibility",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "dew_point_2m",
            "uv_index",
        ]

        daily_params = [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "sunrise",
            "sunset",
            "precipitation_sum",
            "rain_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "wind_direction_10m_dominant",
        ]

        return (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current={','.join(current_params)}"
            f"&hourly={','.join(hourly_params)}"
            f"&daily={','.join(daily_params)}"
            "&temperature_unit=celsius"
            "&wind_speed_unit=kmh"
            "&precipitation_unit=mm"
            "&timezone=auto"
        )

    @staticmethod
    def _fetch_api_data(url: str) -> dict[str, Any]:
        """Fetch data from the Open-Meteo API."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error accessing Open-Meteo API: {e}"
            raise RuntimeError(error_msg) from e
        except requests.exceptions.RequestException as e:
            error_msg = f"Open-Meteo request failed: {e}"
            raise RuntimeError(error_msg) from e

    def _parse_current_weather(
        self,
        data: dict[str, Any],
        utc_now: datetime,
        time_now: datetime,
        daily_sunrise_map: dict,
        daily_sunset_map: dict,
    ) -> WeatherReading:
        current_data = data.get("current", {})
        current_time_str = current_data.get("time")
        if current_time_str:
            local_time = datetime.fromisoformat(current_time_str).replace(tzinfo=time_now.tzinfo)
            utc_time = local_time.astimezone(UTC)
        else:
            utc_time = utc_now
            local_time = time_now

        daily_data = data.get("daily", {})
        today_max = None
        today_min = None
        if daily_data and daily_data.get("time"):
            today_max = daily_data.get("temperature_2m_max", [None])[0]
            today_min = daily_data.get("temperature_2m_min", [None])[0]

        sunrise = daily_sunrise_map.get(local_time.date())
        sunset = daily_sunset_map.get(local_time.date())
        astral_info = build_astral_info(
            local_time=local_time,
            sunrise=sunrise,
            sunset=sunset,
            sunrise_icon_name=self._icon_provider.sunrise_icon_name,
            sunset_icon_name=self._icon_provider.sunset_icon_name,
        )

        weather_code = current_data.get("weather_code", 0)
        title = wmo_code_to_title(weather_code)
        display_info = self._icon_provider.get_display_info(weather_code, is_daytime(local_time, astral_info))

        current_sky = SkyCondition(
            title=title,
            description=title,
            icon_info=display_info,
            cloud_cover=current_data.get("cloud_cover") / 100 if current_data.get("cloud_cover") is not None else None,
            visibility=None,
            uv_index=None,
        )

        return WeatherReading(
            utc_time=utc_time,
            local_time=local_time,
            temperature=Temperature(
                reading=current_data.get("temperature_2m") or 0.0,
                high=today_max,
                low=today_min,
                feels_like=current_data.get("apparent_temperature"),
            ),
            sky=current_sky,
            wind=Wind(
                speed=current_data.get("wind_speed_10m") or 0.0,
                deg=current_data.get("wind_direction_10m"),
                direction=self._deg_to_compass(current_data.get("wind_direction_10m")),
                gust=current_data.get("wind_gusts_10m"),
            ),
            astral_info=astral_info,
            precipitation_icon_name=self._icon_provider.precipitation_icon_name,
            precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
            wind_icon_name=self._icon_provider.wind_icon_name,
            wind_unicode_char=self._icon_provider.get_wind_unicode(),
            summary=title,
            precip_probability=None,
            rain=current_data.get("rain"),
            pressure=current_data.get("pressure_msl"),
            humidity=current_data.get("relative_humidity_2m") / 100 if current_data.get("relative_humidity_2m") is not None else None,
            dew_point=None,
        )

    def _parse_hourly_forecast(
        self,
        data: dict[str, Any],
        time_now: datetime,
        daily_sunrise_map: dict,
        daily_sunset_map: dict,
    ) -> list[WeatherReading]:
        hourly: list[WeatherReading] = []
        hourly_data = data.get("hourly", {})
        hourly_times = hourly_data.get("time", [])

        for i, time_str in enumerate(hourly_times):
            local_ts = datetime.fromisoformat(time_str).replace(tzinfo=time_now.tzinfo)
            if local_ts < time_now:
                continue

            utc_ts = local_ts.astimezone(UTC)
            sunrise = daily_sunrise_map.get(local_ts.date())
            sunset = daily_sunset_map.get(local_ts.date())
            astral_info = build_astral_info(
                local_time=local_ts,
                sunrise=sunrise,
                sunset=sunset,
                sunrise_icon_name=self._icon_provider.sunrise_icon_name,
                sunset_icon_name=self._icon_provider.sunset_icon_name,
            )

            hour_weather_code = self._get_index(hourly_data.get("weather_code"), i) or 0
            hour_title = wmo_code_to_title(hour_weather_code)
            display_info = self._icon_provider.get_display_info(hour_weather_code, is_daytime(local_ts, astral_info))

            hour_sky = SkyCondition(
                title=hour_title,
                description=hour_title,
                icon_info=display_info,
                cloud_cover=self._get_index(hourly_data.get("cloud_cover"), i) / 100 if self._get_index(hourly_data.get("cloud_cover"), i) is not None else None,
                visibility=self._get_index(hourly_data.get("visibility"), i),
                uv_index=self._get_index(hourly_data.get("uv_index"), i) / 100 if self._get_index(hourly_data.get("uv_index"), i) is not None else None,
            )

            hourly.append(
                WeatherReading(
                    utc_time=utc_ts,
                    local_time=local_ts,
                    temperature=Temperature(
                        reading=self._get_index(hourly_data.get("temperature_2m"), i) or 0.0,
                        feels_like=self._get_index(hourly_data.get("apparent_temperature"), i),
                    ),
                    sky=hour_sky,
                    wind=Wind(
                        speed=self._get_index(hourly_data.get("wind_speed_10m"), i) or 0.0,
                        deg=self._get_index(hourly_data.get("wind_direction_10m"), i),
                        direction=self._deg_to_compass(self._get_index(hourly_data.get("wind_direction_10m"), i)),
                        gust=self._get_index(hourly_data.get("wind_gusts_10m"), i),
                    ),
                    astral_info=astral_info,
                    precipitation_icon_name=self._icon_provider.precipitation_icon_name,
                    precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
                    wind_icon_name=self._icon_provider.wind_icon_name,
                    wind_unicode_char=self._icon_provider.get_wind_unicode(),
                    summary=hour_title,
                    precip_probability=self._get_index(hourly_data.get("precipitation_probability"), i) / 100 if self._get_index(hourly_data.get("precipitation_probability"), i) is not None else None,
                    rain=self._get_index(hourly_data.get("rain"), i),
                    pressure=self._get_index(hourly_data.get("pressure_msl"), i),
                    humidity=self._get_index(hourly_data.get("relative_humidity_2m"), i) / 100 if self._get_index(hourly_data.get("relative_humidity_2m"), i) is not None else None,
                    dew_point=self._get_index(hourly_data.get("dew_point_2m"), i),
                )
            )

        return hourly

    def _parse_daily_forecast(
        self,
        data: dict[str, Any],
        time_now: datetime,
        daily_sunrise_map: dict,
        daily_sunset_map: dict,
    ) -> list[WeatherReading]:
        daily: list[WeatherReading] = []
        daily_data = data.get("daily", {})
        daily_times = daily_data.get("time", [])

        for i, date_str in enumerate(daily_times):
            local_ts = datetime.fromisoformat(date_str).replace(tzinfo=time_now.tzinfo)
            local_ts = local_ts.replace(hour=12, minute=0, second=0, microsecond=0)
            utc_ts = local_ts.astimezone(UTC)

            if local_ts.date() < time_now.date():
                continue

            reading = self._build_daily_reading(daily_data, i, utc_ts, local_ts, daily_sunrise_map, daily_sunset_map)
            daily.append(reading)

        return daily

    def _build_daily_reading(
        self,
        daily_data: dict[str, Any],
        index: int,
        utc_ts: datetime,
        local_ts: datetime,
        daily_sunrise_map: dict,
        daily_sunset_map: dict,
    ) -> WeatherReading:
        day_weather_code = self._get_index(daily_data.get("weather_code"), index) or 0
        day_title = wmo_code_to_title(day_weather_code)
        sunrise = daily_sunrise_map.get(local_ts.date())
        sunset = daily_sunset_map.get(local_ts.date())
        astral_info = build_astral_info(
            local_time=local_ts,
            sunrise=sunrise,
            sunset=sunset,
            sunrise_icon_name=self._icon_provider.sunrise_icon_name,
            sunset_icon_name=self._icon_provider.sunset_icon_name,
        )
        display_info = self._icon_provider.get_display_info(day_weather_code, True)

        day_sky = SkyCondition(
            title=day_title,
            description=day_title,
            icon_info=display_info,
            cloud_cover=None,
            visibility=None,
            uv_index=None,
        )

        temp_max = self._get_index(daily_data.get("temperature_2m_max"), index)
        temp_min = self._get_index(daily_data.get("temperature_2m_min"), index)
        temp_avg = ((temp_max or 0) + (temp_min or 0)) / 2 if temp_max is not None and temp_min is not None else None

        apparent_max = self._get_index(daily_data.get("apparent_temperature_max"), index) or 0
        apparent_min = self._get_index(daily_data.get("apparent_temperature_min"), index) or 0
        feels_like_avg = (apparent_max + apparent_min) / 2 if apparent_max or apparent_min else None

        return WeatherReading(
            utc_time=utc_ts,
            local_time=local_ts,
            temperature=Temperature(
                reading=temp_avg or 0.0,
                high=temp_max,
                low=temp_min,
                feels_like=feels_like_avg,
            ),
            sky=day_sky,
            wind=Wind(
                speed=self._get_index(daily_data.get("wind_speed_10m_max"), index) or 0.0,
                deg=self._get_index(daily_data.get("wind_direction_10m_dominant"), index),
                direction=self._deg_to_compass(self._get_index(daily_data.get("wind_direction_10m_dominant"), index)),
                gust=self._get_index(daily_data.get("wind_gusts_10m_max"), index),
            ),
            astral_info=astral_info,
            precipitation_icon_name=self._icon_provider.precipitation_icon_name,
            precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
            wind_icon_name=self._icon_provider.wind_icon_name,
            wind_unicode_char=self._icon_provider.get_wind_unicode(),
            summary=day_title,
            precip_probability=self._get_index(daily_data.get("precipitation_probability_max"), index) / 100 if self._get_index(daily_data.get("precipitation_probability_max"), index) is not None else None,
            rain=self._get_index(daily_data.get("rain_sum"), index),
            pressure=None,
            humidity=None,
            dew_point=None,
        )

    @staticmethod
    def _get_index(data: list | None, index: int) -> Any:
        if data is None or index >= len(data):
            return None
        return data[index]

    @staticmethod
    def _deg_to_compass(deg: float | None) -> str:
        if deg is None:
            return ""
        return _COMPASS[round(deg / 22.5) % 16]
