"""WeatherClient main client module."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pyowm.commons.exceptions import UnauthorizedError

from .icon_provider import WeatherIconProvider
from .providers.open_meteo_provider import OpenMeteoProvider
from .providers.owm_provider import OWMProvider

if TYPE_CHECKING:
    from .models import WeatherData


class WeatherClient:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        owm_api_key: str | None = None,
        icon_library: str = "meteocons",
        icon_theme: str | None = None,
    ):
        """Initialize the WeatherClient.

        Args:
            latitude: Latitude of the location to fetch weather for.
            longitude: Longitude of the location to fetch weather for.
            owm_api_key: Optional OpenWeatherMap API key for enhanced data.
            icon_library: Icon library to use for display metadata.
            icon_theme: Optional icon theme/style for the selected library.
        """
        self.latitude = latitude
        self.longitude = longitude
        self._icon_provider = WeatherIconProvider(icon_library, icon_theme)
        self._owm = OWMProvider(owm_api_key, self._icon_provider) if owm_api_key else None
        self._open_meteo = OpenMeteoProvider(self._icon_provider)

    def get_weather(self, first_choice: str | None = None, owm_api_key: str | None = None) -> WeatherData:
        """Fetch weather data from providers, falling back as needed.

        This method will try to get the current and forecast weather data from the following providers in order:
        1. OpenWeatherMap v3 "One Call" service (if a valid API key is available that has a one-call subscription)
        2. OpenWeatherMap v2.5 free service (if a valid OWM free API key is available)
        3. Open-Meteo (as a fallback if OWM fails or is unavailable)

        The preferred provider order can be influenced by the `first_choice` argument, but the method will automatically
        fall back to the next provider if the first choice fails for any reason (e.g., network error, API error, invalid API key).

        Args:
            first_choice(str | None): Optional string indicating the preferred weather provider ("owm" or "open_meteo").
            owm_api_key(str | None): Optional OpenWeatherMap API key to use for this fetch.
                         If provided, it will override the client's default key for this call.

        Raises:
            RuntimeError: If all providers fail to fetch weather data.

        Returns:
            A WeatherData object containing the current reading, list of hourly readings, and weather station info.
        """
        if first_choice == "owm" or (first_choice is None and self._owm):
            try:
                return self.get_open_weather_map_weather(owm_api_key=owm_api_key)
            except UnauthorizedError:
                return self.get_open_meteo_weather()
            except RuntimeError as e:
                try:
                    return self.get_open_meteo_weather()
                except Exception as fallback_error:  # noqa: BLE001
                    error_msg = f"OpenWeatherMap fetch failed: {e}. Open-Meteo fallback failed: {fallback_error}."
                    raise RuntimeError(error_msg) from fallback_error

        try:
            return self.get_open_meteo_weather()
        except NotImplementedError as e:
            error_msg = f"Open-Meteo fetch failed: {e}. No other providers available."
            raise RuntimeError(error_msg) from e
        except RuntimeError as e:
            error_msg = f"Open-Meteo fetch failed: {e}. No other providers available."
            raise RuntimeError(error_msg) from e
        except Exception:  # Return OWM data if Open-Meteo fails for any other reason  # noqa: BLE001
            return self.get_open_weather_map_weather(owm_api_key=owm_api_key)

    def get_open_weather_map_weather(self, owm_api_key: str | None = None) -> WeatherData:
        """Fetch weather data from OpenWeatherMap.

        Args:
            owm_api_key: Optional OpenWeatherMap API key to use for this fetch.
                         If provided, it will override the client's default key for this call.

        Raises:
            RuntimeError: If the OWM API key is not set or if the request fails.

        Returns:
            A WeatherData object containing the current reading, list of hourly readings, and weather station info.
        """
        if owm_api_key:
            self._owm = OWMProvider(owm_api_key, self._icon_provider)

        if self._owm:
            return self._owm.fetch(self.latitude, self.longitude)
        error_msg = "OpenWeatherMap API key is required for this method."
        raise RuntimeError(error_msg)

    def get_open_meteo_weather(self) -> WeatherData:
        """Fetch weather data from Open Meteo.

        Returns:
            A WeatherData object containing the current reading, list of hourly readings, and weather station info.
        """
        return self._open_meteo.fetch(self.latitude, self.longitude)
