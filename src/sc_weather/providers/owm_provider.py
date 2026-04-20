"""WeatherClient provider for OpenWeatherMap (OWM) API.

Refer to the documentation for details on the endpoints used:
https://nickelseyspelloc.github.io/sc-weather

"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import requests
from pyowm import OWM
from pyowm.commons.exceptions import APIRequestError, UnauthorizedError
from pyowm.weatherapi30.weather import Weather
from sc_foundation import DateHelper

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
    owm_code_to_wmo,
    wmo_code_to_title,
)

if TYPE_CHECKING:
    from ..icon_provider import WeatherIconProvider


_COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


class OWMProvider:
    def __init__(self, api_key: str, icon_provider: WeatherIconProvider):
        self._api_key = api_key
        self._icon_provider = icon_provider
        self._owm = OWM(api_key)
        self._mgr = self._owm.weather_manager()

    def fetch(self, lat: float, lon: float) -> WeatherData:  # noqa: PLR0914
        """Fetch weather data from OpenWeatherMap.

        Returns:
            Weather data from the One Call API, or the free-tier fallback.

        Raises:
            RuntimeError: If the request to OpenWeatherMap fails.
        """
        try:
            one_call = self._mgr.one_call(lat=lat, lon=lon, units="celsius")
        except UnauthorizedError:
            return self._fetch_free(lat, lon)
        except APIRequestError as e:
            error_msg = f"OpenWeatherMap request failed: {e}"
            raise RuntimeError(error_msg) from e

        local_tz = datetime.now().astimezone().tzinfo
        utc_now = datetime.now(UTC)
        time_now = datetime.now(tz=local_tz)

        hourly_data = one_call.forecast_hourly or []
        daily_data = one_call.forecast_daily or []
        today_data = daily_data[0] if daily_data else None
        current_data = one_call.current

        current_astral = self._build_astral_info_for_times(
            time_now,
            self._owm_time_to_datetime(current_data.sunrise_time("unix"), get_local=True),
            self._owm_time_to_datetime(current_data.sunset_time("unix"), get_local=True),
        )
        current_sky = self._build_sky_condition(
            title=current_data.status,
            description=current_data.detailed_status,
            owm_code=current_data.weather_code,
            local_time=time_now,
            astral_info=current_astral,
            cloud_cover=current_data.clouds / 100 if current_data.clouds is not None else None,
            visibility=current_data.visibility_distance,
            uv_index=current_data.uvi / 100 if current_data.uvi is not None else None,
        )

        current_reading = WeatherReading(
            utc_time=utc_now,
            local_time=time_now,
            temperature=Temperature(
                reading=current_data.temperature("celsius")["temp"],
                high=today_data.temperature("celsius")["max"] if today_data else None,
                low=today_data.temperature("celsius")["min"] if today_data else None,
                feels_like=today_data.temperature("celsius").get("feels_like_day") if today_data else None,
            ),
            sky=current_sky,
            wind=Wind(
                speed=self._covert_wind_speed(current_data.wind()["speed"]),
                deg=current_data.wind().get("deg"),
                direction=self._deg_to_compass(current_data.wind().get("deg")),
                gust=self._covert_wind_speed(current_data.wind().get("gust", 0.0)) if "gust" in current_data.wind() else None,
            ),
            astral_info=current_astral,
            precipitation_icon_name=self._icon_provider.precipitation_icon_name,
            precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
            wind_icon_name=self._icon_provider.wind_icon_name,
            wind_unicode_char=self._icon_provider.get_wind_unicode(),
            summary=current_data.detailed_status,
            precip_probability=current_data.precipitation_probability if current_data.precipitation_probability is not None else None,
            rain=self._get_rain(today_data, "all"),
            pressure=current_data.pressure["press"] if current_data.pressure else None,
            humidity=current_data.humidity / 100 if current_data.humidity is not None else None,
            dew_point=self._convert_kelvin_to_celsius(current_data.dewpoint) if current_data.dewpoint else None,
        )

        hourly: list[WeatherReading] = []
        for hour in hourly_data:
            utc_timestamp = self._convert_unix_time_to_datetime(hour.ref_time)
            local_timestamp = self._convert_unix_time_to_datetime(hour.ref_time, get_local=True)
            if local_timestamp < time_now:
                continue

            hour_astral = self._build_astral_info_for_times(local_timestamp, current_astral.sunrise, current_astral.sunset)
            hour_sky = self._build_sky_condition(
                title=hour.status,
                description=hour.detailed_status,
                owm_code=hour.weather_code,
                local_time=local_timestamp,
                astral_info=hour_astral,
                cloud_cover=hour.clouds / 100 if hour.clouds is not None else None,
                visibility=hour.visibility_distance,
                uv_index=hour.uvi / 100 if hour.uvi is not None else None,
            )

            hourly.append(
                WeatherReading(
                    utc_time=utc_timestamp,
                    local_time=local_timestamp,
                    temperature=Temperature(
                        reading=hour.temperature("celsius")["temp"],
                        feels_like=hour.temperature("celsius").get("feels_like"),
                    ),
                    sky=hour_sky,
                    wind=Wind(
                        speed=self._covert_wind_speed(hour.wind()["speed"]),
                        deg=hour.wind().get("deg"),
                        direction=self._deg_to_compass(hour.wind().get("deg")),
                        gust=self._covert_wind_speed(hour.wind().get("gust", 0.0)) if "gust" in hour.wind() else None,
                    ),
                    astral_info=hour_astral,
                    precipitation_icon_name=self._icon_provider.precipitation_icon_name,
                    precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
                    wind_icon_name=self._icon_provider.wind_icon_name,
                    wind_unicode_char=self._icon_provider.get_wind_unicode(),
                    summary=hour.detailed_status,
                    precip_probability=hour.precipitation_probability if hour.precipitation_probability is not None else None,
                    rain=self._get_rain(hour, "1hr"),
                    pressure=hour.pressure["press"] if hour.pressure else None,
                    humidity=hour.humidity / 100 if hour.humidity is not None else None,
                    dew_point=self._convert_kelvin_to_celsius(hour.dewpoint) if hour.dewpoint else None,
                )
            )

        daily: list[WeatherReading] = []
        for day in daily_data:
            utc_timestamp = self._convert_unix_time_to_datetime(day.ref_time)
            local_timestamp = self._convert_unix_time_to_datetime(day.ref_time, get_local=True)
            if local_timestamp < time_now:
                continue

            day_astral = self._build_astral_info_for_times(
                local_timestamp,
                self._owm_time_to_datetime(day.sunrise_time("unix"), get_local=True) or current_astral.sunrise,
                self._owm_time_to_datetime(day.sunset_time("unix"), get_local=True) or current_astral.sunset,
            )
            day_sky = self._build_sky_condition(
                title=day.status,
                description=day.detailed_status,
                owm_code=day.weather_code,
                local_time=local_timestamp,
                astral_info=day_astral,
                cloud_cover=day.clouds / 100 if day.clouds is not None else None,
                visibility=day.visibility_distance,
                uv_index=day.uvi / 100 if day.uvi is not None else None,
            )

            daily.append(
                WeatherReading(
                    utc_time=utc_timestamp,
                    local_time=local_timestamp,
                    temperature=Temperature(
                        reading=day.temperature("celsius")["day"],
                        high=day.temperature("celsius")["max"],
                        low=day.temperature("celsius")["min"],
                        feels_like=day.temperature("celsius").get("feels_like_day"),
                    ),
                    sky=day_sky,
                    wind=Wind(
                        speed=self._covert_wind_speed(day.wind()["speed"]),
                        deg=day.wind().get("deg"),
                        direction=self._deg_to_compass(day.wind().get("deg")),
                    ),
                    astral_info=day_astral,
                    precipitation_icon_name=self._icon_provider.precipitation_icon_name,
                    precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
                    wind_icon_name=self._icon_provider.wind_icon_name,
                    wind_unicode_char=self._icon_provider.get_wind_unicode(),
                    summary=day.detailed_status,
                    precip_probability=day.precipitation_probability if day.precipitation_probability is not None else None,
                    rain=self._get_rain(day, "all"),
                    pressure=day.pressure["press"] if day.pressure else None,
                    humidity=day.humidity / 100 if day.humidity is not None else None,
                    dew_point=self._convert_kelvin_to_celsius(day.dewpoint) if day.dewpoint else None,
                )
            )

        station = WeatherStation("OpenWeatherMap One Call API", lat, lon)
        return WeatherData(current=current_reading, hourly=hourly, daily=daily, station=station, as_at=datetime.now(tz=local_tz))

    def _fetch_free(self, lat: float, lon: float) -> WeatherData:  # noqa: PLR0914, PLR0915
        """Use free-tier endpoints: current weather + 5 day / 3 hour forecast.

        Returns:
            Weather data assembled from the free-tier current and forecast APIs.

        Raises:
            RuntimeError: If either free-tier request fails.
        """
        current_url = "https://api.openweathermap.org/data/2.5/weather"
        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": lat, "lon": lon, "appid": self._api_key, "units": "metric"}

        try:
            current_resp = requests.get(current_url, params=params, timeout=10)
            current_resp.raise_for_status()
            current_data: dict = current_resp.json()
        except UnauthorizedError as e:
            error_msg = f"Unauthorized access to OpenWeatherMap free API current weather: {e}"
            raise RuntimeError(error_msg) from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = f"Unauthorized access to OpenWeatherMap free API current weather: {e}"
                raise RuntimeError(error_msg) from e
            error_msg = f"HTTP error accessing OpenWeatherMap free API current weather: {e}"
            raise RuntimeError(error_msg) from e

        local_tz = datetime.now().astimezone().tzinfo
        utc_now = datetime.now(UTC)
        time_now = datetime.now(tz=local_tz)

        current_weather = (current_data.get("weather") or [{}])[0] or {}
        current_wind = current_data.get("wind") or {}
        current_main = current_data.get("main") or {}
        astral_data = DateHelper.get_dawn_dusk_times(lat, lon)
        current_astral = self._build_astral_info_for_times(
            time_now,
            sunrise.astimezone() if (sunrise := astral_data.get("sunrise")) is not None else None,
            sunset.astimezone() if (sunset := astral_data.get("sunset")) is not None else None,
        )
        current_sky = self._build_sky_condition(
            title=current_weather.get("main", "unknown"),
            description=current_weather.get("description", "unknown"),
            owm_code=current_weather.get("id"),
            local_time=time_now,
            astral_info=current_astral,
            cloud_cover=current_data.get("clouds", {}).get("all", 0) / 100 if current_data.get("clouds") else None,
            visibility=current_data.get("visibility"),
            uv_index=None,
        )

        current_reading = WeatherReading(
            utc_time=utc_now,
            local_time=time_now,
            temperature=Temperature(
                reading=current_main.get("temp") or 0.0,
                high=current_main.get("temp_max") or 0.0,
                low=current_main.get("temp_min") or 0.0,
                feels_like=current_main.get("feels_like") or 0.0,
            ),
            sky=current_sky,
            wind=Wind(
                speed=self._covert_wind_speed(current_wind.get("speed", 0.0)),
                deg=current_wind.get("deg"),
                direction=self._deg_to_compass(current_wind.get("deg")),
                gust=self._covert_wind_speed(current_wind.get("gust", 0.0)) if "gust" in current_wind else None,
            ),
            astral_info=current_astral,
            precipitation_icon_name=self._icon_provider.precipitation_icon_name,
            precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
            wind_icon_name=self._icon_provider.wind_icon_name,
            wind_unicode_char=self._icon_provider.get_wind_unicode(),
            rain=self._get_rain(current_data, "1hr"),
            pressure=current_main.get("pressure"),
            humidity=(current_main.get("humidity") or 0) / 100 if current_main.get("humidity") is not None else None,
        )

        try:
            forecast_resp = requests.get(forecast_url, params=params, timeout=10)
            forecast_resp.raise_for_status()
            forecast_data: dict[str, Any] = forecast_resp.json()
        except UnauthorizedError as e:
            error_msg = f"Unauthorized access to OpenWeatherMap free API forecast: {e}"
            raise RuntimeError(error_msg) from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = f"Unauthorized access to OpenWeatherMap free API forecast: {e}"
                raise RuntimeError(error_msg) from e
            error_msg = f"HTTP error accessing OpenWeatherMap free API forecast: {e}"
            raise RuntimeError(error_msg) from e

        hourly: list[WeatherReading] = []
        for item in forecast_data.get("list", []):
            utc_ts = datetime.fromtimestamp(int(item.get("dt", 0)), tz=UTC)
            if utc_ts < utc_now:
                continue

            weather = (item.get("weather") or [{}])[0] or {}
            wind = item.get("wind") or {}
            main = item.get("main") or {}
            local_time = utc_ts.astimezone()
            astral_data = DateHelper.get_dawn_dusk_times(lat, lon, as_at=utc_ts.date())
            hour_astral = self._build_astral_info_for_times(
                local_time,
                sunrise.astimezone() if (sunrise := astral_data.get("sunrise")) is not None else None,
                sunset.astimezone() if (sunset := astral_data.get("sunset")) is not None else None,
            )
            hour_sky = self._build_sky_condition(
                title=weather.get("main", "unknown"),
                description=weather.get("description", "unknown"),
                owm_code=weather.get("id"),
                local_time=local_time,
                astral_info=hour_astral,
                cloud_cover=item.get("clouds", {}).get("all", 0) / 100 if item.get("clouds") else None,
                visibility=item.get("visibility"),
                uv_index=None,
            )

            hourly.append(
                WeatherReading(
                    utc_time=utc_ts,
                    local_time=local_time,
                    temperature=Temperature(
                        reading=main.get("temp") or 0.0,
                        high=main.get("temp_max") or 0.0,
                        low=main.get("temp_min") or 0.0,
                        feels_like=main.get("feels_like") or 0.0,
                    ),
                    sky=hour_sky,
                    wind=Wind(
                        speed=self._covert_wind_speed(wind.get("speed", 0.0)),
                        deg=wind.get("deg"),
                        direction=self._deg_to_compass(wind.get("deg")),
                        gust=self._covert_wind_speed(wind.get("gust", 0.0)) if "gust" in wind else None,
                    ),
                    astral_info=hour_astral,
                    precipitation_icon_name=self._icon_provider.precipitation_icon_name,
                    precipitation_unicode_char=self._icon_provider.get_precipitation_unicode(),
                    wind_icon_name=self._icon_provider.wind_icon_name,
                    wind_unicode_char=self._icon_provider.get_wind_unicode(),
                    precip_probability=item.get("pop") if item.get("pop") is not None else None,
                    rain=self._get_rain(item, "3h"),
                    pressure=main.get("pressure"),
                    humidity=(main.get("humidity") or 0) / 100 if main.get("humidity") is not None else None,
                )
            )

        station = WeatherStation("OpenWeatherMap Free API", lat, lon)
        return WeatherData(current=current_reading, hourly=hourly, daily=[], station=station, as_at=datetime.now(tz=local_tz))

    def _build_astral_info_for_times(self, local_time: datetime, sunrise: datetime | None, sunset: datetime | None):
        return build_astral_info(
            local_time=local_time,
            sunrise=sunrise,
            sunset=sunset,
            sunrise_icon_name=self._icon_provider.sunrise_icon_name,
            sunset_icon_name=self._icon_provider.sunset_icon_name,
        )

    def _build_sky_condition(
        self,
        *,
        title: str,
        description: str,
        owm_code: int | None,
        local_time: datetime,
        astral_info,
        cloud_cover: float | None,
        visibility: int | None,
        uv_index: float | None,
    ) -> SkyCondition:
        wmo_code = owm_code_to_wmo(owm_code)
        display_info = self._icon_provider.get_display_info(wmo_code, is_daytime(local_time, astral_info))
        fallback_title = wmo_code_to_title(wmo_code)
        return SkyCondition(
            title=title or fallback_title,
            description=description or fallback_title,
            icon_info=display_info,
            cloud_cover=cloud_cover,
            visibility=visibility,
            uv_index=uv_index,
        )

    @staticmethod
    def _covert_wind_speed(wind: float) -> float:
        return round(wind * 3.6, 2)

    @staticmethod
    def _get_rain(rain_data: list[Weather] | Weather | dict | None, key: str) -> float | None:
        if not rain_data:
            return None
        if isinstance(rain_data, list):
            src_weather = rain_data[0]
            rain = src_weather.rain
        elif isinstance(rain_data, Weather):
            src_weather = rain_data
            rain = src_weather.rain
        elif isinstance(rain_data, dict):
            src_weather = rain_data
            rain = src_weather.get("rain")
        else:
            return None

        if rain and key in rain:
            return round(float(rain[key]), 2)
        return None

    @staticmethod
    def _convert_unix_time_to_datetime(unix_time: int, get_local: bool = False) -> datetime:
        dt = datetime.fromtimestamp(unix_time, tz=UTC)
        if get_local:
            dt = dt.astimezone()
        return dt

    @classmethod
    def _owm_time_to_datetime(cls, value: int | str | datetime | None, get_local: bool = False) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
            return dt.astimezone() if get_local else dt.astimezone(UTC)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                return None
        return cls._convert_unix_time_to_datetime(value, get_local=get_local)

    @staticmethod
    def _convert_kelvin_to_celsius(kelvin_temp: float) -> float:
        return round(kelvin_temp - 273.15, 2)

    @staticmethod
    def _deg_to_compass(deg: float | None) -> str:
        if deg is None:
            return ""
        return _COMPASS[round(deg / 22.5) % 16]
