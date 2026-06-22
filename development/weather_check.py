"""
Weather client example script.

This script demonstrates usage of the WeatherClient to fetch current weather,
hourly forecasts, station information, and bundled SVG icon references for
Sydney, Australia coordinates.

Environment Variables:
    OWM_API_KEY: OpenWeatherMap API key required for weather data access.
                 This environment variable must be set before running the script.

The script fetches weather data for coordinates (-33.86, 151.21) representing
Sydney and prints current conditions, station info, and the number of hourly
forecast data points available.
"""
# ruff: noqa: I001

import os
import sys
from pathlib import Path
from pprint import pprint
from typing import TypedDict

# Allow running this example directly from a src/ layout checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sc_weather
from sc_weather import WeatherClient
from sc_weather.icon_provider import WeatherIconProvider
from sc_weather.models import WeatherReading


ICON_LIBRARY = "meteocons"
ICON_THEME = "fill-animated"
# ICON_LIBRARY = "weather-icons"
# ICON_THEME = "monochrome-black-static"
IS_CROPPED = True  # Whether to use cropped icons (no padding) or original versions.
STATIC_ICON_PREFIX = "/static/weather-icons"
type ReadingIconRefs = dict[str, str | None]


class WeatherIconRefs(TypedDict):
    current: ReadingIconRefs
    hourly: list[ReadingIconRefs]
    daily: list[ReadingIconRefs]


def get_weather_icons_root() -> Path:
    package_root = Path(sc_weather.__file__).resolve().parent
    return package_root / "weather_icons"


def build_icon_url(icon_provider: WeatherIconProvider, icon_name: str, *, static_prefix: str = STATIC_ICON_PREFIX) -> str:  # noqa: ARG001
    """Build a URL that a FastAPI/ASGI app could serve as a static SVG asset.

    Returns:
        A URL path for a packaged weather icon SVG.
    """
    # prefix_path = static_prefix.rstrip('/')
    prefix_path = get_weather_icons_root()
    icon_rel_path = icon_provider.get_icon_relative_path(icon_name)
    return f"{prefix_path}/{icon_rel_path}"


def build_reading_icon_refs(icon_provider: WeatherIconProvider, reading: WeatherReading) -> ReadingIconRefs:
    """Create ASGI-friendly image references for a weather reading.

    Returns:
        A mapping of semantic icon roles to static URL paths.
    """
    return {
        "condition_icon": build_icon_url(icon_provider, reading.sky.icon_info.icon_name),
        "sunrise_icon": build_icon_url(icon_provider, reading.astral_info.sunrise_icon_name),
        "sunset_icon": build_icon_url(icon_provider, reading.astral_info.sunset_icon_name),
        "precipitation_icon": build_icon_url(icon_provider, reading.precipitation_icon_name),
        "wind_icon": build_icon_url(icon_provider, reading.wind_icon_name),
    }


def build_weather_icon_refs(icon_provider: WeatherIconProvider, weather_data) -> WeatherIconRefs:
    """Collect image references for the current, hourly, and daily readings.

    Returns:
        A mapping containing icon URL references for current, hourly, and daily data.
    """
    return {
        "current": build_reading_icon_refs(icon_provider, weather_data.current),
        "hourly": [build_reading_icon_refs(icon_provider, reading) for reading in weather_data.hourly],
        "daily": [build_reading_icon_refs(icon_provider, reading) for reading in weather_data.daily],
    }


def main() -> None:
    api_key = os.environ.get("OWM_API_KEY_V3")
    # api_key = os.environ.get("OWM_API_KEY_FREE")
    latitude = 43.0
    longitude = 12.7

    client = WeatherClient(
        latitude=latitude,
        longitude=longitude,
        owm_api_key=api_key,
        icon_library=ICON_LIBRARY,
        icon_theme=ICON_THEME,
    )
    icon_provider = WeatherIconProvider(library=ICON_LIBRARY, theme=ICON_THEME, is_cropped=IS_CROPPED)
    icon_name = "raindrop"
    print(f"Example icon URL: {build_icon_url(icon_provider, icon_name)}")
    print(f"get_icon_relative_path(): {icon_provider.get_icon_relative_path(icon_name)}")
    print(f"get_icon_resource(): {icon_provider.get_icon_resource(icon_name)}")

    weather_data = client.get_weather(first_choice="owm")
    weather_icon_refs = build_weather_icon_refs(icon_provider, weather_data)

    print(f"\n\nWeather data for Sydney, Australia (lat: {latitude}, lon: {longitude})")
    print(f"Icon library: {ICON_LIBRARY}, theme: {ICON_THEME}")

    print("Current weather:")
    pprint(weather_data.current, indent=4)
    print(f"timestamp: {weather_data.current.local_time.strftime('%H:%M')}\n"
        f"sky: {weather_data.current.sky.description}\n"
        f"icon_name: {weather_data.current.sky.icon_info.icon_name}°C\n")

    print("Current icon refs:")
    pprint(weather_icon_refs["current"], indent=4)
    print(f"Station: {weather_data.station}")

    print(len(weather_data.hourly), "hourly points")
    for hour in weather_data.hourly[:24]:  # Print the first 24 hourly forecasts
        print(f"timestamp: {hour.local_time.strftime('%H:%M')}\n"
        f"sky: {hour.sky.description}\n"
        f"icon_name: {hour.sky.icon_info.icon_name}°C\n")

    print(len(weather_data.daily), "daily points")
    for day in weather_data.daily:
        print(f"Day: {day.local_time.strftime('%a %d %B')}\n"
        f"sky: {day.sky.description}\n"
        f"icon_name: {day.sky.icon_info.icon_name}°C\n")


if __name__ == "__main__":
    main()
