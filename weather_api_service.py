import requests
import os

from requests import ConnectionError
from datetime import datetime
from typing import NamedTuple, Literal
from enum import Enum

from exceptions import ApiServiceError

# this code shows up when city not found
ERROR = "404"

API_TOKEN = os.getenv("OPEN_WEATHER_API_TOKEN")

OPENWEATHER_URL_INPLACE = (
        "https://api.openweathermap.org/data/2.5/weather?"
        "lat={latitude}&lon={longitude}&"
        "appid=" + API_TOKEN + "&lang=en&"
                               "units=metric"
)

OPENWEATHER_URL_BY_CITY = (
        "https://api.openweathermap.org/data/2.5/weather?"
        "q={city}&appid=" + API_TOKEN + "&units=metric"
)

OPENWEATHER_URL_AIR = ("http://api.openweathermap.org/data/2.5/air_pollution?"
                       "lat={latitude}&lon={longitude}&"
                       "appid=" + API_TOKEN)

Celsius = float
Humidity = int
City = str
Country = str


class Coordinates(NamedTuple):
    latitude: float
    longitude: float


class WeatherType(Enum):
    THUNDERSTORM = 'Thunderstorm \U0001F329'
    DRIZZLE = 'Drizzle \U0001F327'
    RAIN = 'Rain \U0001F327'
    SNOW = 'Snow \U0001F328'
    CLEAR = 'Clear \u2600️'
    FOG = 'Fog \U0001F32B'
    CLOUDS = 'Clouds \u2601'


class AirQualityType(Enum):
    GOOD = 'Good 😊'
    FAIR = 'Fair 😌'
    MODERATE = 'Moderate 😐'
    POOR = 'Poor 😞'
    VERY_POOR = 'Very Poor 😢'


class Weather(NamedTuple):
    temperature: Celsius
    feels_like: Celsius
    temperature_min: Celsius
    temperature_max: Celsius
    humidity: Humidity
    weather_type: WeatherType
    sunrise: datetime
    sunset: datetime
    city: City
    country: Country


def get_weather(openweather_response: dict) -> Weather:
    """Returns parsed weather data"""
    weather = _parse_openweather_response(openweather_response)
    return weather


def get_openweather_response(latitude: float, longitude: float) -> dict:
    """Returns raw weather data by GEO"""
    url = requests.get(OPENWEATHER_URL_INPLACE.format(
        latitude=latitude, longitude=longitude))
    try:
        return url.json()
    except ConnectionError:
        raise ApiServiceError


def get_openweather_air_response(latitude: float, longitude: float) -> dict:
    """ Return Air Quality Index"""
    url = requests.get(OPENWEATHER_URL_AIR.format(latitude=latitude, longitude=longitude))
    try:
        return url.json()
    except ConnectionError:
        raise ApiServiceError


def get_openweather_city_response(response: str) -> dict:
    """Returns raw weather data by City"""
    url = requests.get(OPENWEATHER_URL_BY_CITY.format(city=response))
    try:
        return url.json()
    except ConnectionError:
        raise ApiServiceError


def get_coordinates_by_city(openweather_city_response: dict) -> Coordinates:
    lat = openweather_city_response["coord"]["lat"]
    lon = openweather_city_response["coord"]["lon"]
    coordinates = Coordinates(longitude=lon, latitude=lat)
    return coordinates


def _parse_openweather_response(openweather_dict: dict) -> Weather:
    return Weather(
        temperature=_parse_temp(openweather_dict, 'temp'),
        feels_like=_parse_temp(openweather_dict, 'feels_like'),
        temperature_min=_parse_temp(openweather_dict, 'temp_min'),
        temperature_max=_parse_temp(openweather_dict, 'temp_max'),
        humidity=_parse_humidity(openweather_dict),
        weather_type=_parse_weather_type(openweather_dict),
        sunrise=_parse_sun_time(openweather_dict, 'sunrise'),
        sunset=_parse_sun_time(openweather_dict, 'sunset'),
        city=_parse_city(openweather_dict),
        country=_parse_country(openweather_dict)
    )


def _parse_temp(openweather_dict: dict,
                temp: Literal['temp'] or Literal['feels_like'] or
                      Literal['temp_max'] or Literal['temp_min']) -> Celsius:
    return openweather_dict['main'][temp]


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
        "80": WeatherType.CLOUDS
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
        "5": AirQualityType.VERY_POOR
    }
    for _id, _air_type in air_types.items():
        if air_type_id.startswith(_id):
            return _air_type
    raise ApiServiceError


def _parse_sun_time(
        openweather_dict: dict,
        time: Literal["sunrise"] or Literal["sunset"]) -> datetime:
    return datetime.fromtimestamp(openweather_dict["sys"][time])


def _parse_city(openweather_dict: dict) -> City:
    try:
        return openweather_dict["name"]
    except KeyError:
        raise ApiServiceError


def _parse_country(openweather_dict: dict) -> Country:
    try:
        return openweather_dict["sys"]["country"]
    except KeyError:
        raise ApiServiceError
