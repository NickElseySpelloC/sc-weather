"""Shared weather-condition normalization helpers."""
from __future__ import annotations

from datetime import datetime, timedelta

from .models import AstralInfo, WeatherCondition

WMO_CODE_DETAILS: dict[int, tuple[str, WeatherCondition]] = {
    0: ("Clear sky", WeatherCondition.CLEAR),
    1: ("Mainly clear", WeatherCondition.PARTLY_CLOUDY),
    2: ("Partly cloudy", WeatherCondition.PARTLY_CLOUDY),
    3: ("Overcast", WeatherCondition.OVERCAST),
    4: ("Smoke", WeatherCondition.SMOKE),
    5: ("Haze", WeatherCondition.HAZE),
    6: ("Dust in suspension", WeatherCondition.DUST),
    7: ("Dust or sand raised by wind", WeatherCondition.DUST),
    18: ("Squalls", WeatherCondition.WIND),
    19: ("Funnel cloud", WeatherCondition.WIND),
    45: ("Fog", WeatherCondition.FOG),
    48: ("Depositing rime fog", WeatherCondition.FOG),
    51: ("Light drizzle", WeatherCondition.DRIZZLE),
    53: ("Moderate drizzle", WeatherCondition.DRIZZLE),
    55: ("Dense drizzle", WeatherCondition.DRIZZLE),
    56: ("Light freezing drizzle", WeatherCondition.SLEET),
    57: ("Dense freezing drizzle", WeatherCondition.SLEET),
    61: ("Slight rain", WeatherCondition.RAIN),
    63: ("Moderate rain", WeatherCondition.RAIN),
    65: ("Heavy rain", WeatherCondition.RAIN),
    66: ("Light freezing rain", WeatherCondition.SLEET),
    67: ("Heavy freezing rain", WeatherCondition.SLEET),
    71: ("Slight snow", WeatherCondition.SNOW),
    73: ("Moderate snow", WeatherCondition.SNOW),
    75: ("Heavy snow", WeatherCondition.SNOW),
    77: ("Snow grains", WeatherCondition.SNOW),
    80: ("Slight rain showers", WeatherCondition.RAIN),
    81: ("Moderate rain showers", WeatherCondition.RAIN),
    82: ("Violent rain showers", WeatherCondition.RAIN),
    85: ("Slight snow showers", WeatherCondition.SNOW),
    86: ("Heavy snow showers", WeatherCondition.SNOW),
    95: ("Thunderstorm", WeatherCondition.THUNDERSTORM),
    96: ("Thunderstorm with slight hail", WeatherCondition.THUNDERSTORM),
    99: ("Thunderstorm with heavy hail", WeatherCondition.THUNDERSTORM),
}

OWM_CODE_TO_WMO: dict[int, int] = {
    200: 95,
    201: 95,
    202: 99,
    210: 95,
    211: 95,
    212: 99,
    221: 95,
    230: 95,
    231: 95,
    232: 99,
    300: 51,
    301: 53,
    302: 55,
    310: 51,
    311: 53,
    312: 55,
    313: 53,
    314: 55,
    321: 51,
    500: 61,
    501: 63,
    502: 65,
    503: 65,
    504: 65,
    511: 67,
    520: 80,
    521: 81,
    522: 82,
    531: 82,
    600: 71,
    601: 73,
    602: 75,
    611: 67,
    612: 77,
    613: 77,
    615: 67,
    616: 67,
    620: 85,
    621: 86,
    622: 86,
    701: 45,
    711: 4,
    721: 5,
    731: 6,
    741: 45,
    751: 6,
    761: 6,
    762: 7,
    771: 18,
    781: 19,
    800: 0,
    801: 1,
    802: 2,
    803: 3,
    804: 3,
}

CONDITION_UNICODE: dict[WeatherCondition, str] = {
    WeatherCondition.UNKNOWN: "🌡️",
    WeatherCondition.CLEAR: "☀️",
    WeatherCondition.PARTLY_CLOUDY: "⛅",
    WeatherCondition.CLOUDY: "☁️",
    WeatherCondition.OVERCAST: "☁️",
    WeatherCondition.FOG: "🌫️",
    WeatherCondition.DRIZZLE: "🌦️",
    WeatherCondition.RAIN: "🌧️",
    WeatherCondition.SLEET: "🌨️",
    WeatherCondition.SNOW: "❄️",
    WeatherCondition.HAIL: "🧊",
    WeatherCondition.THUNDERSTORM: "⛈️",
    WeatherCondition.HAZE: "🌫️",
    WeatherCondition.SMOKE: "🌫️",
    WeatherCondition.DUST: "🌫️",
    WeatherCondition.WIND: "💨",
}

SUNRISE_UNICODE = "🌅"
SUNSET_UNICODE = "🌇"
PRECIPITATION_UNICODE = "💧"
WIND_UNICODE = "💨"


def wmo_code_to_condition(wmo_code: int) -> WeatherCondition:
    """Return the normalized condition for a WMO code.

    Args:
        wmo_code: The WMO code to translate.

    Returns:
        The corresponding WeatherCondition.
    """
    return WMO_CODE_DETAILS.get(wmo_code, ("Unknown", WeatherCondition.UNKNOWN))[1]


def wmo_code_to_title(wmo_code: int) -> str:
    """Return a human-friendly title for a WMO code.

    Args:
        wmo_code: The WMO code to translate.

    Returns:
        A human-friendly title for the WMO code.
    """
    return WMO_CODE_DETAILS.get(wmo_code, ("Unknown", WeatherCondition.UNKNOWN))[0]


def owm_code_to_wmo(owm_code: int | None) -> int:
    """Translate an OpenWeatherMap code into a WMO code.

    Args:
        owm_code: The OpenWeatherMap code to translate.

    Returns:
        The corresponding WMO code, or 0 when the input is missing or unknown.
    """
    if owm_code is None:
        return 0
    return OWM_CODE_TO_WMO.get(owm_code, 0)


def build_astral_info(
    *,
    local_time: datetime,
    sunrise: datetime | None,
    sunset: datetime | None,
    sunrise_icon_name: str,
    sunset_icon_name: str,
) -> AstralInfo:
    """Build astral metadata, falling back to 6am/6pm if needed.

    This ensures sunrise and sunset are timezone-aligned with local_time and remain
    logically ordered.

    Args:
        local_time: The current local time for the location.
        sunrise: The sunrise time, which may be None or timezone-aware.
        sunset: The sunset time, which may be None or timezone-aware.
        sunrise_icon_name: The icon name to use for sunrise.
        sunset_icon_name: The icon name to use for sunset.

    Returns:
        An AstralInfo object containing normalized sunrise/sunset times and icon metadata.
    """
    tzinfo = local_time.tzinfo
    if sunrise is None:
        sunrise = local_time.replace(hour=6, minute=0, second=0, microsecond=0)
    elif tzinfo is not None and sunrise.tzinfo is not None:
        sunrise = sunrise.astimezone(tzinfo)

    if sunset is None:
        sunset = local_time.replace(hour=18, minute=0, second=0, microsecond=0)
    elif tzinfo is not None and sunset.tzinfo is not None:
        sunset = sunset.astimezone(tzinfo)

    if sunset <= sunrise:
        sunset = sunrise + timedelta(hours=12)

    return AstralInfo(
        sunrise=sunrise,
        sunset=sunset,
        sunrise_icon_name=sunrise_icon_name,
        sunrise_unicode_char=SUNRISE_UNICODE,
        sunset_icon_name=sunset_icon_name,
        sunset_unicode_char=SUNSET_UNICODE,
    )


def is_daytime(local_time: datetime, astral_info: AstralInfo) -> bool:
    """Determine whether a timestamp falls between sunrise and sunset.

    Args:
        local_time: The local timestamp to evaluate.
        astral_info: Sunrise and sunset information for the location.

    Returns:
        True when local_time is within the sunrise-to-sunset interval.
    """
    return astral_info.sunrise <= local_time < astral_info.sunset
