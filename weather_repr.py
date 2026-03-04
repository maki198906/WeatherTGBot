from datetime import datetime

from flag import flag

from weather_api_service import ForecastDay, Weather


def feels_like_emoji(temp: float) -> str:
    """Returns an emoji that reflects how the temperature feels."""
    if temp <= -15:
        return "\U0001f976"   # 🥶 freezing
    if temp <= 0:
        return "\U0001f9ca"   # 🧐 cold
    if temp <= 10:
        return "\U0001f32c\ufe0f"  # 🌬 windy/cool
    if temp <= 20:
        return "\U0001f60a"   # 😊 comfortable
    if temp <= 30:
        return "\u2600\ufe0f"  # ☀️ warm
    return "\U0001f525"       # 🔥 hot


def weather_repr(weather: Weather) -> str:
    """Formats location-based weather data to readable representation."""
    return (
        f"{weather.city} {flag(weather.country or 'None')}\n"
        f"\U0001f321 Temperature: {weather.temperature}\u00b0C\n"
        f"{weather.weather_type.value}\n"
        f"Feels like: {weather.feels_like}\u00b0C {feels_like_emoji(weather.feels_like)}\n"
        f"Max: {weather.temperature_max}\u00b0C  Min: {weather.temperature_min}\u00b0C\n"
        f"\U0001f4a7 Humidity: {weather.humidity}%\n"
        f"\U0001f4a8 Wind: {weather.wind_speed} m/s\n"
        f"\U0001f53d Pressure: {weather.pressure} hPa\n"
    )


def weather_repr_city(weather: Weather) -> str:
    """Formats city-based weather data to readable representation."""
    return (
        f"{weather.city} {flag(weather.country)}\n"
        f"\U0001f321 Temperature: {weather.temperature}\u00b0C\n"
        f"{weather.weather_type.value}\n"
        f"Feels like: {weather.feels_like}\u00b0C {feels_like_emoji(weather.feels_like)}\n"
        f"Max: {weather.temperature_max}\u00b0C  Min: {weather.temperature_min}\u00b0C\n"
        f"\U0001f4a7 Humidity: {weather.humidity}%\n"
        f"\U0001f4a8 Wind: {weather.wind_speed} m/s\n"
        f"\U0001f53d Pressure: {weather.pressure} hPa\n"
    )


def forecast_repr(days: list[ForecastDay], city_name: str, country_code: str) -> str:
    """Formats 5-day forecast to readable HTML representation."""
    try:
        country_flag = flag(country_code)
    except Exception:
        country_flag = ""
    lines = [f"\U0001f4c5 <b>5-day forecast \u2014 {city_name} {country_flag}</b>\n"]
    for day in days:
        dt = datetime.strptime(day.date, "%Y-%m-%d")
        day_name = dt.strftime("%a %b %d")
        lines.append(
            f"<b>{day_name}</b>\n"
            f"  {day.weather_type.value}\n"
            f"  \U0001f321 {day.temperature_min:.0f}\u00b0C \u2013 {day.temperature_max:.0f}\u00b0C"
            f"   \U0001f4a8 {day.wind_speed} m/s\n"
        )
    return "\n".join(lines)
