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
    THUNDERSTORM = "Thunderstorm \U0001F329"
    DRIZZLE = "Drizzle \U0001F327"
    RAIN = "Rain \U0001F327"
    SNOW = "Snow \U0001F328"
    CLEAR = "Clear \u2600\uFE0F"
    FOG = "Fog \U0001F32B"
    CLOUDS = "Clouds \u2601"


class AirQualityType(Enum):
    GOOD = "Good \U0001F60A"
    FAIR = "Fair \U0001F60C"
    MODERATE = "Moderate \U0001F610"
    POOR = "Poor \U0001F61E"
    VERY_POOR = "Very Poor \U0001F622"


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


def get_weather(openweather_response: dict) -> Weather:
    """Returns parsed weather data"""
    return _parse_openweather_response(openweather_response)


def get_openweather_response(latitude: float, longitude: float) -> dict:
    """Returns raw weather data by coordinates"""
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
    """Returns Air Quality Index"""
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
    """Returns raw weather data by city name"""
    url = (
        f"{OPENWEATHER_BASE}/weather?"
        f"q={city}&appid={_api_token()}&units=metric"
    )
    try:
        return requests.get(url).json()
    except ConnectionError:
        raise ApiServiceError


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
        weather_type_id = str(openweather_dict["weather"][0]["id"])
    except (IndexError, KeyError):
        raise ApiServiceError
    weather_types = {
        "2": WeatherType.THUNDERSTORM,
        "3": WeatherType.DRIZZLE,
        "5": WeatherType.RAIN,
        "6": WeatherType.SNOW,
        "7": WeatherType.FOG,
        "800": WeatherType.CLEAR,
        "80": WeatherType.CLOUDS,
    }
    for _id, _weather_type in weather_types.items():
        if weather_type_id.startswith(_id):
            return _weather_type
    raise ApiServiceError


def get_air_quality_type(openweather_dict: dict) -> AirQualityType:
    """Returns air quality type using AQI"""
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
