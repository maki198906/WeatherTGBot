import os
import requests

from datetime import datetime
from enum import Enum
from typing import Literal, NamedTuple, Optional

from dotenv import load_dotenv
from requests import ConnectionError

from exceptions import ApiServiceError

load_dotenv()

# this code shows up when city not found
ERROR = "404"

Celsius = float
Humidity = int

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_AIR_BASE = "http://api.openweathermap.org/data/2.5"


def _api_token() -> str:
    """Read token at call time so it is never baked in as None."""
    token = os.getenv("OPEN_WEATHER_API_TOKEN")
    if not token:
        raise RuntimeError("OPEN_WEATHER_API_TOKEN is not set")
    return token


class Locality:
    city: Optional[str] = None
    country: Optional[str] = None


class Coordinates(NamedTuple):
    latitude: float
    longitude: float


class WeatherType(Enum):
    THUNDERSTORM = "Thunderstorm \u26c8"
    DRIZZLE = "Drizzle \U0001f326"
    RAIN = "Rain \U0001f327"
    SNOW = "Snow \u2744\ufe0f"
    CLEAR = "Clear \u2600\ufe0f"
    FOG = "Fog \U0001f32b"
    CLOUDS = "Clouds \u26c5"


class AirQualityType(Enum):
    GOOD = "Good \U0001f60a"
    FAIR = "Fair \U0001f60c"
    MODERATE = "Moderate \U0001f610"
    POOR = "Poor \U0001f61e"
    VERY_POOR = "Very Poor \U0001f622"


class Weather(NamedTuple):
    temperature: Celsius
    feels_like: Celsius
    temperature_min: Celsius
    temperature_max: Celsius
    humidity: Humidity
    weather_type: WeatherType
    sunrise: datetime
    sunset: datetime
    city: Locality
    country: Locality
    wind_speed: float = 0.0
    pressure: int = 0


class ForecastDay(NamedTuple):
    date: str           # e.g. "2026-03-05"
    temperature_min: Celsius
    temperature_max: Celsius
    weather_type: WeatherType
    wind_speed: float


_WEATHER_TYPE_MAP = {
    "2": WeatherType.THUNDERSTORM,
    "3": WeatherType.DRIZZLE,
    "5": WeatherType.RAIN,
    "6": WeatherType.SNOW,
    "7": WeatherType.FOG,
    "800": WeatherType.CLEAR,
    "80": WeatherType.CLOUDS,
}


def _resolve_weather_type(weather_id: int) -> WeatherType:
    id_str = str(weather_id)
    for prefix, wtype in _WEATHER_TYPE_MAP.items():
        if id_str.startswith(prefix):
            return wtype
    return WeatherType.CLOUDS


def get_weather(openweather_response: dict) -> Weather:
    """Returns parsed weather data."""
    return _parse_openweather_response(openweather_response)


def get_openweather_response(latitude: float, longitude: float) -> dict:
    """Returns raw weather data by coordinates."""
    url = (
        f"{OPENWEATHER_BASE}/weather?"
        f"lat={latitude}&lon={longitude}&"
        f"appid={_api_token()}&lang=en&units=metric"
    )
    try:
        return requests.get(url).json()
    except ConnectionError:
        raise ApiServiceError


def get_openweather_air_response(latitude: float, longitude: float) -> dict:
    """Returns Air Quality Index."""
    url = (
        f"{OPENWEATHER_AIR_BASE}/air_pollution?"
        f"lat={latitude}&lon={longitude}&"
        f"appid={_api_token()}"
    )
    try:
        return requests.get(url).json()
    except ConnectionError:
        raise ApiServiceError


def get_openweather_city_response(city: str) -> dict:
    """Returns raw weather data by city name."""
    url = (
        f"{OPENWEATHER_BASE}/weather?"
        f"q={city}&appid={_api_token()}&units=metric"
    )
    try:
        return requests.get(url).json()
    except ConnectionError:
        raise ApiServiceError


def get_forecast_response(city: str) -> dict:
    """Returns 5-day / 3-hour forecast by city name."""
    url = (
        f"{OPENWEATHER_BASE}/forecast?"
        f"q={city}&appid={_api_token()}&units=metric&lang=en"
    )
    try:
        return requests.get(url).json()
    except ConnectionError:
        raise ApiServiceError


def get_forecast_by_coords(latitude: float, longitude: float) -> dict:
    """Returns 5-day / 3-hour forecast by coordinates."""
    url = (
        f"{OPENWEATHER_BASE}/forecast?"
        f"lat={latitude}&lon={longitude}&appid={_api_token()}&units=metric&lang=en"
    )
    try:
        return requests.get(url).json()
    except ConnectionError:
        raise ApiServiceError


def parse_forecast(forecast_response: dict) -> list[ForecastDay]:
    """Returns one ForecastDay per calendar day (prefers the noon slot)."""
    days: dict[str, ForecastDay] = {}
    for item in forecast_response.get("list", []):
        dt_txt = item.get("dt_txt", "")
        date = dt_txt[:10]
        hour = dt_txt[11:13]
        if not date:
            continue
        try:
            entry = ForecastDay(
                date=date,
                temperature_min=item["main"]["temp_min"],
                temperature_max=item["main"]["temp_max"],
                weather_type=_resolve_weather_type(item["weather"][0]["id"]),
                wind_speed=round(item["wind"]["speed"], 1),
            )
        except (KeyError, IndexError):
            continue
        if date not in days or hour == "12":
            days[date] = entry
    return list(days.values())[:5]


def get_coordinates_by_city(openweather_city_response: dict) -> Coordinates:
    lat = openweather_city_response["coord"]["lat"]
    lon = openweather_city_response["coord"]["lon"]
    return Coordinates(latitude=lat, longitude=lon)


def _parse_openweather_response(openweather_dict: dict) -> Weather:
    return Weather(
        temperature=_parse_temp(openweather_dict, "temp"),
        feels_like=_parse_temp(openweather_dict, "feels_like"),
        temperature_min=_parse_temp(openweather_dict, "temp_min"),
        temperature_max=_parse_temp(openweather_dict, "temp_max"),
        humidity=_parse_humidity(openweather_dict),
        weather_type=_parse_weather_type(openweather_dict),
        sunrise=_parse_sun_time(openweather_dict, "sunrise"),
        sunset=_parse_sun_time(openweather_dict, "sunset"),
        city=_parse_city(openweather_dict),
        country=_parse_country(openweather_dict),
        wind_speed=round(openweather_dict.get("wind", {}).get("speed", 0.0), 1),
        pressure=openweather_dict.get("main", {}).get("pressure", 0),
    )


def _parse_temp(
    openweather_dict: dict,
    temp: Literal["temp", "feels_like", "temp_max", "temp_min"],
) -> Celsius:
    return openweather_dict["main"][temp]


def _parse_humidity(openweather_dict: dict) -> Humidity:
    return openweather_dict["main"]["humidity"]


def _parse_weather_type(openweather_dict: dict) -> WeatherType:
    try:
        return _resolve_weather_type(openweather_dict["weather"][0]["id"])
    except (IndexError, KeyError):
        raise ApiServiceError


def get_air_quality_type(openweather_dict: dict) -> AirQualityType:
    """Returns air quality type using AQI."""
    try:
        air_type_id = str(openweather_dict["list"][0]["main"]["aqi"])
    except (IndexError, KeyError):
        raise ApiServiceError
    air_types = {
        "1": AirQualityType.GOOD,
        "2": AirQualityType.FAIR,
        "3": AirQualityType.MODERATE,
        "4": AirQualityType.POOR,
        "5": AirQualityType.VERY_POOR,
    }
    for _id, _air_type in air_types.items():
        if air_type_id.startswith(_id):
            return _air_type
    raise ApiServiceError


def _parse_sun_time(
    openweather_dict: dict,
    time: Literal["sunrise", "sunset"],
) -> datetime:
    return datetime.fromtimestamp(openweather_dict["sys"][time])


def _parse_city(openweather_dict: dict) -> Locality:
    try:
        return openweather_dict["name"]
    except KeyError:
        raise ApiServiceError


def _parse_country(openweather_dict: dict) -> Locality:
    try:
        return openweather_dict["sys"].setdefault("country", Locality.country)
    except KeyError:
        raise ApiServiceError
