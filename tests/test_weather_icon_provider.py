from __future__ import annotations

from sc_weather.icon_provider import WeatherIconProvider
from sc_weather.models import WeatherCondition


def test_meteocons_default_theme_supports_packaged_icons():
    provider = WeatherIconProvider()
    display = provider.get_display_info(0, is_day=True)

    assert provider.library == "meteocons"
    assert display.condition_key == WeatherCondition.CLEAR
    assert display.icon_name == "clear-day"
    assert provider.get_icon_resource(display.icon_name).is_file()


def test_weather_icons_library_supports_svg_lookup():
    provider = WeatherIconProvider("weather-icons")
    display = provider.get_display_info(61, is_day=False)

    assert provider.theme == "monochrome-black-static"
    assert display.icon_name == "wi-night-alt-rain"
    assert provider.get_icon_resource(display.icon_name).is_file()
