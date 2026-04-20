# WeatherClient

This class provides a simple wrapper for the OpenWeathermap (OWM) and Open Meteo weather providers. It returns the current and forecast weather for the designated location.

The class will attempt to retrieve the weather data from the providers in this order:

  1. OWM paid subscription (valid OWM "One Call" API Key required).
  2. OWM free tier (valid OWM free server API Key required).
  3. Open Meteo weather (no API key needed)

For the first two options, an OWM API key is required. You can obtain one at https://openweathermap.org.

Weather conditions are normalized to WMO weather codes internally so both providers return the same sky-condition model. Each reading includes:

1. A normalized `WeatherDisplayInfo` payload with the WMO code, canonical condition enum, day/night variant, icon name, and unicode character.
2. Required `AstralInfo` metadata with sunrise/sunset times plus sunrise/sunset icon names and emoji.
3. Reading-level precipitation and wind icon metadata.

SVG assets for the supported icon libraries are bundled with the package. `WeatherClient` can be configured with:

1. `icon_library="meteocons"` with themes `fill-static`, `fill-animated`, `line-static`, `line-animated`, or `monochrome-static`.
2. `icon_library="weather-icons"` with theme `default`.

The client returns icon names and packaged SVG assets; it does not generate hosted icon URLs. Applications that render icons should serve the bundled SVGs themselves or export them via the icon provider helper.

In all instances the WeatherClient weather look methods (e.g. get_weather()) return a WeatherData dataclass:

```python
  {%
    include "../src/sc_weather/models.py"
  %}
```

::: sc_weather.WeatherClient

