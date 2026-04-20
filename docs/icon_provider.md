# Icon Provider

This is a helper weather_client class that can be used to resolve weather icon into references that a client web application can use.

The sc_utility library currently supports the following weather icon libraries:

| key | Library Name | GitHub source | 
|:--|:--|:--|
| meteocons | Meteocons | [basmilius weather-icons](https://github.com/basmilius/weather-icons) | 
| weather-icons | Erik Flowers “Weather Icons” | [erikflowers weather-icons](https://github.com/erikflowers/weather-icons) | 

The key is used in the library argument when initialising the WeatherIconProvider class:

```python
from pathlib import Path

import weather_client
from weather_client.icon_provider import WeatherIconProvider


ICON_LIBRARY = "meteocons"
ICON_THEME = "fill-animated"
STATIC_ICON_PREFIX = "/static/weather-icons"


def build_icon_url(icon_provider: WeatherIconProvider, icon_name: str) -> str:
    prefix_path = Path(weather_client.__file__).resolve().parent / "weather_icons"
    icon_rel_path = icon_provider.get_icon_relative_path(icon_name)
    return f"{prefix_path}/{icon_rel_path}"


icon_provider = WeatherIconProvider(library=ICON_LIBRARY, theme=ICON_THEME, is_cropped=True)
icon_name = "raindrop"
print(f"Example icon URL: {build_icon_url(icon_provider, icon_name)}")
```

The icon library's support different themes. Within each theme, an uncropped and cropped version of the SVG image is provided. The uncropped version is an original copy from the developer's Github repo. The cropped version removes most of the whitespace around the active elements of the image. 

Note that this library includes the /scripts/crop_svg_viewbox.py whcih can be used to crop the excess whitespace from the default SVG files. For example, we used this command to crop the meteocons files:

```bash
uv run scripts/crop_svg_viewbox.py src/weather_client/weather_icons/meteocons/default src/weather_client/weather_icons/meteocons/cropped --target-fill 0.9
```

The following themes are supported

| key | Themes | Cropping style | 
|:--|:--|:--|
| meteocons | fill-static<br>fill-animated<br>line-static<br>line-animated<br>monochrome-black-static<br>monochrome-white-static | cropped<br>uncropped |
| weather-icons | monochrome-black-static<br>monochrome-white-static | cropped<br>uncropped | 


::: sc_weather.icon_provider.WeatherIconProvider
