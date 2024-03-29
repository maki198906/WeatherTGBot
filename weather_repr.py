from weather_api_service import Weather
from flag import flag


def weather_repr(weather: Weather) -> str:
    """Formats weather data to readable representation """
    return (f"{weather.city} {flag(weather.country or 'None')}\n"
            f"Temperature: {weather.temperature}°C\n"
            f"{weather.weather_type.value}\n"
            f"Feels like: {weather.feels_like}°C\n"
            f"Max temperature: {weather.temperature_max}°C\n"
            f"Min temperature: {weather.temperature_min}°C\n"
            f"Humidity: {weather.humidity}%\n"
            )


def weather_repr_city(weather: Weather) -> str:
    """Formats weather data to readable representation """
    return (f"{weather.city} {flag(weather.country)}\n"
            f"Temperature: {weather.temperature}°C\n"
            f"{weather.weather_type.value}\n"
            f"Feels like: {weather.feels_like}°C\n"
            f"Max temperature: {weather.temperature_max}°C\n"
            f"Min temperature: {weather.temperature_min}°C\n"
            f"Humidity: {weather.humidity}%\n"
            )
