"""Data models for WeatherClient."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class WeatherCondition(Enum):
    """Normalized weather conditions used across providers and icon libraries."""

    UNKNOWN = "unknown"
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    SLEET = "sleet"
    SNOW = "snow"
    HAIL = "hail"
    THUNDERSTORM = "thunderstorm"
    HAZE = "haze"
    SMOKE = "smoke"
    DUST = "dust"
    WIND = "wind"


@dataclass
class Temperature:
    reading: float
    high: float | None = None
    low: float | None = None
    feels_like: float | None = None
    units: str = "C"


@dataclass
class WeatherDisplayInfo:
    wmo_code: int
    condition_key: WeatherCondition
    day_night_variant: str | None
    icon_name: str
    unicode_char: str | None = None


@dataclass
class SkyCondition:
    title: str
    description: str
    icon_info: WeatherDisplayInfo
    cloud_cover: float | None = None
    visibility: int | None = None
    uv_index: float | None = None


@dataclass
class Wind:
    speed: float
    deg: float | None
    direction: str | None = None
    gust: float | None = None
    units: str = "km/h"


@dataclass
class AstralInfo:
    sunrise: datetime
    sunset: datetime
    sunrise_icon_name: str
    sunrise_unicode_char: str
    sunset_icon_name: str
    sunset_unicode_char: str


@dataclass
class WeatherReading:
    utc_time: datetime
    local_time: datetime
    temperature: Temperature
    sky: SkyCondition
    wind: Wind
    astral_info: AstralInfo
    precipitation_icon_name: str
    precipitation_unicode_char: str
    wind_icon_name: str
    wind_unicode_char: str
    summary: str | None = None
    precip_probability: float | None = None
    rain: float | None = None
    pressure: float | None = None
    humidity: float | None = None
    dew_point: float | None = None


@dataclass
class WeatherStation:
    source: str
    latitude: float
    longitude: float
    timezone_name: str | None = None
    timezone_offset: int | None = None


@dataclass
class WeatherData:
    current: WeatherReading
    hourly: list[WeatherReading]
    daily: list[WeatherReading]
    station: WeatherStation
    as_at: datetime
