"""Icon-provider support for weather display metadata."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from shutil import copytree
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

from .models import WeatherCondition, WeatherDisplayInfo
from .normalization import (
    CONDITION_UNICODE,
    PRECIPITATION_UNICODE,
    WIND_UNICODE,
    wmo_code_to_condition,
)


@dataclass(frozen=True)
class _ResolvedIcon:
    name: str
    variant: str | None


class _BaseIconMapper:
    library: ClassVar[str]
    default_theme: ClassVar[str]
    default_is_cropped: ClassVar[bool] = False
    supported_themes: ClassVar[tuple[str, ...]]
    theme_paths: ClassVar[dict[str, str]]
    cropped_paths: ClassVar[dict[bool, str]] = {
        False: "uncropped",
        True: "cropped",
    }
    condition_icons: ClassVar[dict[WeatherCondition, str | dict[str, str]]]
    sunrise_icon_name: ClassVar[str]
    sunset_icon_name: ClassVar[str]
    precipitation_icon_name: ClassVar[str]
    wind_icon_name: ClassVar[str]

    def resolve_icon(self, condition: WeatherCondition, is_day: bool | None) -> _ResolvedIcon:
        icon = self.condition_icons.get(condition, self.condition_icons[WeatherCondition.UNKNOWN])
        if isinstance(icon, dict):
            variant = "day" if is_day is not False else "night"
            return _ResolvedIcon(icon[variant], variant)
        return _ResolvedIcon(icon, None)


class _MeteoconsMapper(_BaseIconMapper):
    library: ClassVar[str] = "meteocons"
    default_theme: ClassVar[str] = "fill-static"
    supported_themes: ClassVar[tuple[str, ...]] = (
        "fill-animated",
        "fill-static",
        "line-animated",
        "line-static",
        "monochrome-black-static",
        "monochrome-white-static",
    )
    theme_paths: ClassVar[dict[str, str]] = {
        "fill-animated": "fill/svg-animated",
        "fill-static": "fill/svg-static",
        "line-animated": "line/svg-animated",
        "line-static": "line/svg-static",
        "monochrome-black-static": "monochrome-black/svg-static",
        "monochrome-white-static": "monochrome-white/svg-static",
    }
    condition_icons: ClassVar[dict[WeatherCondition, str | dict[str, str]]] = {
        WeatherCondition.UNKNOWN: "not-available",
        WeatherCondition.CLEAR: {"day": "clear-day", "night": "clear-night"},
        WeatherCondition.PARTLY_CLOUDY: {"day": "partly-cloudy-day", "night": "partly-cloudy-night"},
        WeatherCondition.CLOUDY: "cloudy",
        WeatherCondition.OVERCAST: {"day": "overcast-day", "night": "overcast-night"},
        WeatherCondition.FOG: {"day": "fog-day", "night": "fog-night"},
        WeatherCondition.DRIZZLE: {"day": "overcast-day-drizzle", "night": "overcast-night-drizzle"},
        WeatherCondition.RAIN: {"day": "overcast-day-rain", "night": "overcast-night-rain"},
        WeatherCondition.SLEET: {"day": "overcast-day-sleet", "night": "overcast-night-sleet"},
        WeatherCondition.SNOW: {"day": "overcast-day-snow", "night": "overcast-night-snow"},
        WeatherCondition.HAIL: {"day": "overcast-day-hail", "night": "overcast-night-hail"},
        WeatherCondition.THUNDERSTORM: {"day": "thunderstorms-day", "night": "thunderstorms-night"},
        WeatherCondition.HAZE: {"day": "haze-day", "night": "haze-night"},
        WeatherCondition.SMOKE: "smoke",
        WeatherCondition.DUST: {"day": "dust-day", "night": "dust-night"},
        WeatherCondition.WIND: "wind",
    }
    sunrise_icon_name: ClassVar[str] = "sunrise"
    sunset_icon_name: ClassVar[str] = "sunset"
    precipitation_icon_name: ClassVar[str] = "raindrop"
    wind_icon_name: ClassVar[str] = "windsock"


class _WeatherIconsMapper(_BaseIconMapper):
    library: ClassVar[str] = "weather-icons"
    default_theme: ClassVar[str] = "monochrome-black-static"
    supported_themes: ClassVar[tuple[str, ...]] = (
        "monochrome-black-static",
        "monochrome-white-static",
    )
    theme_paths: ClassVar[dict[str, str]] = {
        "monochrome-black-static": "monochrome-black/svg-static",
        "monochrome-white-static": "monochrome-white/svg-static",
    }
    condition_icons: ClassVar[dict[WeatherCondition, str | dict[str, str]]] = {
        WeatherCondition.UNKNOWN: "wi-na",
        WeatherCondition.CLEAR: {"day": "wi-day-sunny", "night": "wi-night-clear"},
        WeatherCondition.PARTLY_CLOUDY: {"day": "wi-day-cloudy", "night": "wi-night-alt-cloudy"},
        WeatherCondition.CLOUDY: "wi-cloudy",
        WeatherCondition.OVERCAST: "wi-cloudy",
        WeatherCondition.FOG: {"day": "wi-day-fog", "night": "wi-night-fog"},
        WeatherCondition.DRIZZLE: {"day": "wi-day-sprinkle", "night": "wi-night-alt-sprinkle"},
        WeatherCondition.RAIN: {"day": "wi-day-rain", "night": "wi-night-alt-rain"},
        WeatherCondition.SLEET: {"day": "wi-day-sleet", "night": "wi-night-alt-sleet"},
        WeatherCondition.SNOW: {"day": "wi-day-snow", "night": "wi-night-alt-snow"},
        WeatherCondition.HAIL: {"day": "wi-day-hail", "night": "wi-night-alt-hail"},
        WeatherCondition.THUNDERSTORM: {"day": "wi-day-thunderstorm", "night": "wi-night-alt-thunderstorm"},
        WeatherCondition.HAZE: "wi-smog",
        WeatherCondition.SMOKE: "wi-smoke",
        WeatherCondition.DUST: "wi-dust",
        WeatherCondition.WIND: "wi-strong-wind",
    }
    sunrise_icon_name: ClassVar[str] = "wi-sunrise"
    sunset_icon_name: ClassVar[str] = "wi-sunset"
    precipitation_icon_name: ClassVar[str] = "wi-raindrop"
    wind_icon_name: ClassVar[str] = "wi-strong-wind"


_MAPPERS: dict[str, _BaseIconMapper] = {
    _MeteoconsMapper.library: _MeteoconsMapper(),
    _WeatherIconsMapper.library: _WeatherIconsMapper(),
}


class WeatherIconProvider:
    """Resolve normalized weather conditions to icon metadata and assets."""

    def __init__(self, library: str = "meteocons", theme: str | None = None, is_cropped: bool | None = False) -> None:
        """Initialize the provider with a specific icon library and theme.

        Args:
            library (str): The icon library to use. One of ("meteocons", "weather-icons").
            theme (str | None): The theme variant to use within the library (e.g., "fill-static"). If None, the library's default theme will be used.
            is_cropped (bool | None): Whether to use cropped icons. Defaults to False.

        Raises:
            ValueError: If the specified library or theme is not supported.
        """
        if library not in _MAPPERS:
            error_msg = f"Unsupported icon library: {library}"
            raise ValueError(error_msg)

        self._mapper = _MAPPERS[library]
        self.library = library
        self.theme = theme or self._mapper.default_theme
        self.is_cropped = is_cropped or self._mapper.default_is_cropped
        if self.theme not in self._mapper.supported_themes:
            error_msg = f"Unsupported theme '{self.theme}' for icon library '{library}'"
            raise ValueError(error_msg)

    @property
    def supported_themes(self) -> tuple[str, ...]:
        return self._mapper.supported_themes

    @property
    def sunrise_icon_name(self) -> str:
        return self._mapper.sunrise_icon_name

    @property
    def sunset_icon_name(self) -> str:
        return self._mapper.sunset_icon_name

    @property
    def precipitation_icon_name(self) -> str:
        return self._mapper.precipitation_icon_name

    @property
    def wind_icon_name(self) -> str:
        return self._mapper.wind_icon_name

    def get_display_info(self, wmo_code: int, is_day: bool | None = None) -> WeatherDisplayInfo:
        condition = wmo_code_to_condition(wmo_code)
        resolved = self._mapper.resolve_icon(condition, is_day)
        return WeatherDisplayInfo(
            wmo_code=wmo_code,
            condition_key=condition,
            day_night_variant=resolved.variant,
            icon_name=resolved.name,
            unicode_char=CONDITION_UNICODE.get(condition),
        )

    def get_icon_relative_path(self, icon_name: str) -> str:
        """Get the relative path to an icon SVG within the library's resource structure.

        Args:
            icon_name: The name of the icon (without file extension) to retrieve.

        Returns:
            The relative path to the icon SVG.
        """
        return f"{self.library}/{self._mapper.cropped_paths[self.is_cropped]}/{self._mapper.theme_paths[self.theme]}/{icon_name}.svg"

    def get_icon_resource(self, icon_name: str) -> Traversable:
        """Get a reference to the icon SVG resource.

        Args:
            icon_name: The name of the icon (without file extension) to retrieve.

        Returns:
            A reference to the icon SVG resource.
        """
        root = files("sc_weather").joinpath(
            "weather_icons",
            self.library,
            self._mapper.cropped_paths[self.is_cropped],
            self._mapper.theme_paths[self.theme],
        )
        return root.joinpath(f"{icon_name}.svg")

    def get_icon_svg(self, icon_name: str) -> str:
        """Get the SVG content of an icon as a string.

        Args:
            icon_name: The name of the icon (without file extension) to retrieve.

        Returns:
            The SVG content of the icon as a string.
        """
        return self.get_icon_resource(icon_name).read_text(encoding="utf-8")

    def export_icons(self, destination: str | Path) -> Path:
        """Export the icon SVGs for the current library and theme to a local directory.

        Args:
            destination: The base directory to which the icons should be exported. The icons will be placed in a subdirectory structure based on the library and theme.

        Returns:
            The path to the directory containing the exported icons.
        """
        destination_path = Path(destination) / self.library / self._mapper.cropped_paths[self.is_cropped] / self.theme
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        resource_dir = files("sc_weather").joinpath(
            "weather_icons",
            self.library,
            self._mapper.cropped_paths[self.is_cropped],
            self._mapper.theme_paths[self.theme],
        )
        with as_file(resource_dir) as source_dir:
            if destination_path.exists():
                for svg_file in destination_path.glob("*.svg"):
                    svg_file.unlink()
            copytree(source_dir, destination_path, dirs_exist_ok=True)
        return destination_path

    @staticmethod
    def get_precipitation_unicode() -> str:
        return PRECIPITATION_UNICODE

    @staticmethod
    def get_wind_unicode() -> str:
        return WIND_UNICODE
