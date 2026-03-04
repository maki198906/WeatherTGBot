import asyncio
import os
import time
import uuid

# Load .env FIRST — before any custom module is imported
from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ContentType, ParseMode
from aiogram.filters import Command
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from loguru import logger
from timezonefinder import TimezoneFinder

import favourites as fav
import scheduler as sched
import subscriptions
from exceptions import WrongInput
from random_weather import generate_random_coords
from timezoneutils import sun_condition, timezone
from weather_api_service import (
    ERROR,
    Coordinates,
    get_air_quality_type,
    get_coordinates_by_city,
    get_forecast_response,
    get_openweather_air_response,
    get_openweather_city_response,
    get_openweather_response,
    get_weather,
    parse_forecast,
)
from weather_repr import feels_like_emoji, forecast_repr, weather_repr, weather_repr_city

logger.add(
    "log_errors.log",
    format="{time} {level} {message}",
    rotation="5 MB",
    compression="zip",
)

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("TELEGRAM_API_TOKEN is not set — check your .env file")

# Initialize SQLite tables on startup
fav.init_db()
subscriptions.init_subscriptions_table()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

_tf = TimezoneFinder()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_button(lat: float, lon: float) -> types.InlineKeyboardMarkup:
    """Inline keyboard with a direct link to the OpenWeatherMap map."""
    url = (
        f"https://openweathermap.org/weathermap?"
        f"basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=10"
    )
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="\U0001f5fa View on map", url=url)]]
    )


async def _send_city_weather(message: types.Message, city: str) -> None:
    """Fetch and send current weather for a city. Shared by city search and favourite buttons."""
    response = get_openweather_city_response(city)
    if response["cod"] != ERROR:
        coordinates = get_coordinates_by_city(response)
        air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
        air_index_quality = get_air_quality_type(air_index_response)
        area, local_time = timezone(coordinates)
        weather = get_weather(response)
        sun_conditions = sun_condition(
            sunrise=time.mktime(weather.sunrise.timetuple()),
            sunset=time.mktime(weather.sunset.timetuple()),
            coordinates=coordinates,
        )
        weather_represent = weather_repr_city(weather)
        await message.answer(
            f"Time zone: {area}\n"
            f"Local time: {local_time}\n"
            f"Air Index Quality: {air_index_quality.value}\n"
            f"{'*' * 10}\n"
            f"{weather_represent}"
            f"{'*' * 10}\n"
            f"\U0001f305: {sun_conditions.sunrise.strftime('%H:%M')}\n"
            f"\U0001f307: {sun_conditions.sunset.strftime('%H:%M')}",
            reply_markup=_map_button(coordinates.latitude, coordinates.longitude),
        )
        await bot.send_location(message.chat.id, latitude=coordinates.latitude, longitude=coordinates.longitude)
    else:
        await message.answer("Oops, looks like there is no such city\nCheck the spelling")
        raise WrongInput(f'City "{city}" is not defined')


async def _send_subscription_weather(user_id: int, city: str) -> None:
    """Called by the scheduler — sends daily weather directly to a user by ID."""
    try:
        response = get_openweather_city_response(city)
        if response.get("cod") == ERROR:
            logger.warning(f"Subscription: city '{city}' not found for user {user_id}")
            return
        coordinates = get_coordinates_by_city(response)
        air_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
        air_quality = get_air_quality_type(air_response)
        weather = get_weather(response)
        sun_conds = sun_condition(
            sunrise=time.mktime(weather.sunrise.timetuple()),
            sunset=time.mktime(weather.sunset.timetuple()),
            coordinates=coordinates,
        )
        area, local_time = timezone(coordinates)
        weather_text = weather_repr_city(weather)
        await bot.send_message(
            user_id,
            f"\U0001f4cb <b>Cheers! Daily weather for {city}</b>\n\n"
            f"Time zone: {area}\n"
            f"Local time: {local_time}\n"
            f"Air Index Quality: {air_quality.value}\n"
            f"{'*' * 10}\n"
            f"{weather_text}"
            f"{'*' * 10}\n"
            f"\U0001f305: {sun_conds.sunrise.strftime('%H:%M')}\n"
            f"\U0001f307: {sun_conds.sunset.strftime('%H:%M')}",
            parse_mode=ParseMode.HTML,
            reply_markup=_map_button(coordinates.latitude, coordinates.longitude),
        )
        await bot.send_location(user_id, latitude=coordinates.latitude, longitude=coordinates.longitude)
    except Exception as e:
        logger.error(f"Failed to send subscription weather to user {user_id}: {e}")


# ---------------------------------------------------------------------------
# General handlers
# ---------------------------------------------------------------------------

@router.message(Command("start", "help"))
async def send_welcome(message: types.Message):
    """Returns info about what the bot can do."""
    await message.answer(
        "Hi!\nI'm <b>WeWeather</b> Bot\n"
        "I can provide you with the weather around you or more\n\n"
        "\U0001f4cd Just type a city name to get current weather\n"
        "\U0001f4c5 /forecast &lt;city&gt; \u2014 5-day forecast\n"
        "\U0001f4cc /inplace \u2014 weather at your current location\n"
        "\U0001f3b2 /random \u2014 weather at a random spot\n\n"
        "\u2764\ufe0f <b>Favourites</b>\n"
        "/save &lt;city&gt; \u2014 save a city (max 3)\n"
        "/my \u2014 show your saved cities\n"
        "/remove &lt;city&gt; \u2014 remove a saved city\n\n"
        "\u23f0 <b>Daily subscription</b>\n"
        "/subscribe &lt;city&gt; &lt;HH:MM&gt; \u2014 get weather every day at a set time\n"
        "/unsubscribe \u2014 cancel your subscription\n"
        "/mysub \u2014 show your current subscription",
        parse_mode=ParseMode.HTML,
    )


def get_keyboard():
    """Initiates button to share GEO."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="\U0001f30d Share GEO", request_location=True),
                types.KeyboardButton(text="\U0001f6ab Discard"),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Share GEO or Discard",
    )


@router.message(F.text == "\U0001f6ab Discard")
async def discard(message: types.Message):
    await message.answer("Ok pal, I got it!", reply_markup=types.ReplyKeyboardRemove())


@router.message(Command("random"))
async def random_weather(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Click", callback_data="random_weather")]
        ]
    )
    await message.answer("To explore random weather just for fun click me", reply_markup=keyboard)


@router.callback_query(F.data == "random_weather")
@logger.catch
async def send_random_weather(callback: types.CallbackQuery):
    coordinates = generate_random_coords()
    openweather_response = get_openweather_response(coordinates.latitude, coordinates.longitude)
    air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
    air_index_quality = get_air_quality_type(air_index_response)
    weather = get_weather(openweather_response)
    sun_conditions = sun_condition(
        sunrise=time.mktime(weather.sunrise.timetuple()),
        sunset=time.mktime(weather.sunset.timetuple()),
        coordinates=coordinates,
    )
    area, local_time = timezone(coordinates)
    weather_represent = weather_repr(weather)
    await callback.message.answer(
        f"Time zone: {area}\n"
        f"Local time: {local_time}\n"
        f"Air Index Quality: {air_index_quality.value}\n"
        f"{'*' * 10}\n"
        f"{weather_represent}"
        f"{'*' * 10}\n"
        f"\U0001f305: {sun_conditions.sunrise.strftime('%H:%M')}\n"
        f"\U0001f307: {sun_conditions.sunset.strftime('%H:%M')}",
        parse_mode=ParseMode.HTML,
        reply_markup=_map_button(coordinates.latitude, coordinates.longitude),
    )
    await callback.message.answer_location(latitude=coordinates.latitude, longitude=coordinates.longitude)
    await callback.answer()


@router.message(F.content_type == ContentType.LOCATION)
@logger.catch
async def weather_by_location(message: types.Message):
    """Returns readable format of the weather."""
    lat = message.location.latitude
    lon = message.location.longitude
    coordinates = Coordinates(*map(lambda x: round(x, 2), [lat, lon]))
    openweather_response = get_openweather_response(coordinates.latitude, coordinates.longitude)
    air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
    weather = get_weather(openweather_response)
    air_index_quality = get_air_quality_type(air_index_response)
    sun_conditions = sun_condition(
        sunrise=time.mktime(weather.sunrise.timetuple()),
        sunset=time.mktime(weather.sunset.timetuple()),
        coordinates=coordinates,
    )
    area, local_time = timezone(coordinates)
    weather_represent = weather_repr(weather)
    await message.answer(
        f"Time zone: {area}\n"
        f"Local time: {local_time}\n"
        f"Air Index Quality: {air_index_quality.value}\n"
        f"{'*' * 10}\n"
        f"{weather_represent}"
        f"{'*' * 10}\n"
        f"\U0001f305: {sun_conditions.sunrise.strftime('%H:%M')}\n"
        f"\U0001f307: {sun_conditions.sunset.strftime('%H:%M')}",
        reply_markup=_map_button(coordinates.latitude, coordinates.longitude),
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("inplace"))
async def weather_me(message: types.Message):
    """Invokes the location sharing button in Telegram."""
    await message.answer("Click on the button below to share your location", reply_markup=get_keyboard())


@router.message(Command("forecast"))
@logger.catch
async def forecast_command(message: types.Message):
    """Returns a 5-day forecast for a given city."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Please provide a city name:\n/forecast Moscow")
        return
    city = parts[1].strip()
    response = get_forecast_response(city)
    if str(response.get("cod")) == "404":
        await message.answer("Oops, looks like there is no such city\nCheck the spelling")
        return
    days = parse_forecast(response)
    city_name = response.get("city", {}).get("name", city)
    country_code = response.get("city", {}).get("country", "")
    await message.answer(
        forecast_repr(days, city_name, country_code),
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Favourite cities
# ---------------------------------------------------------------------------

@router.message(Command("save"))
@logger.catch
async def save_city_command(message: types.Message):
    """Save a city to the user's favourites."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Please provide a city name:\n/save Stockholm")
        return
    city = parts[1].strip()
    response = get_openweather_city_response(city)
    if str(response.get("cod")) == ERROR:
        await message.answer("\u274c That city wasn't found. Check the spelling before saving.")
        return
    canonical = response.get("name", city)
    status = fav.save_city(message.from_user.id, canonical)
    if status == "saved":
        await message.answer(f"\u2764\ufe0f <b>{canonical}</b> saved to your favourites!", parse_mode=ParseMode.HTML)
    elif status == "duplicate":
        await message.answer(f"\u2139\ufe0f <b>{canonical}</b> is already in your favourites.", parse_mode=ParseMode.HTML)
    elif status == "limit_reached":
        await message.answer(
            f"\u26a0\ufe0f You already have {fav.MAX_CITIES} cities saved.\n"
            "Remove one first with /remove &lt;city&gt;",
            parse_mode=ParseMode.HTML,
        )


@router.message(Command("my"))
async def my_cities_command(message: types.Message):
    """Show the user's saved favourite cities as tappable buttons."""
    cities = fav.get_cities(message.from_user.id)
    if not cities:
        await message.answer(
            "You have no saved cities yet.\nUse /save &lt;city&gt; to add one.",
            parse_mode=ParseMode.HTML,
        )
        return
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=f"\U0001f324 {city}", callback_data=f"fav:{city}")]
            for city in cities
        ]
    )
    await message.answer("\u2764\ufe0f Your favourite cities:", reply_markup=keyboard)


@router.message(Command("remove"))
@logger.catch
async def remove_city_command(message: types.Message):
    """Remove a city from the user's favourites."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Please provide a city name:\n/remove Stockholm")
        return
    city = parts[1].strip()
    removed = fav.remove_city(message.from_user.id, city)
    if removed:
        await message.answer(f"\U0001f5d1 <b>{city}</b> removed from your favourites.", parse_mode=ParseMode.HTML)
    else:
        await message.answer(f"\u2139\ufe0f <b>{city}</b> wasn't in your favourites.", parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("fav:"))
@logger.catch
async def favourite_city_callback(callback: types.CallbackQuery):
    """Fetch and send weather when user taps a favourite city button."""
    city = callback.data[4:]
    await _send_city_weather(callback.message, city)
    await callback.answer()


# ---------------------------------------------------------------------------
# Daily subscription
# ---------------------------------------------------------------------------

@router.message(Command("subscribe"))
@logger.catch
async def subscribe_command(message: types.Message):
    """Subscribe to a daily weather report for a city at a given local time."""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Usage: /subscribe &lt;city&gt; &lt;HH:MM&gt;\n"
            "Example: /subscribe Stockholm 08:00",
            parse_mode=ParseMode.HTML,
        )
        return
    city = parts[1].strip()
    time_str = parts[2].strip()

    # Validate time format
    try:
        hour_str, minute_str = time_str.split(":")
        hour, minute = int(hour_str), int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Invalid time. Use HH:MM format, e.g. 08:00")
        return

    # Validate city
    response = get_openweather_city_response(city)
    if str(response.get("cod")) == ERROR:
        await message.answer("\u274c City not found. Check the spelling.")
        return

    canonical = response.get("name", city)
    coords = get_coordinates_by_city(response)
    tz_name = _tf.timezone_at(lat=coords.latitude, lng=coords.longitude) or "UTC"
    send_time = f"{hour:02d}:{minute:02d}"

    sub = dict(user_id=message.from_user.id, city=canonical, send_time=send_time, tz=tz_name)
    subscriptions.save_subscription(**sub)
    sched.add_or_replace_job(_send_subscription_weather, sub)

    await message.answer(
        f"\u23f0 Subscribed!\n"
        f"You'll receive weather for <b>{canonical}</b> every day at "
        f"<b>{send_time}</b> ({tz_name}).",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("unsubscribe"))
async def unsubscribe_command(message: types.Message):
    """Cancel the user's daily weather subscription."""
    removed = subscriptions.remove_subscription(message.from_user.id)
    sched.remove_job(message.from_user.id)
    if removed:
        await message.answer("\u2705 Your daily subscription has been cancelled.")
    else:
        await message.answer("\u2139\ufe0f You don't have an active subscription.")


@router.message(Command("mysub"))
async def mysub_command(message: types.Message):
    """Show the user's current subscription."""
    sub = subscriptions.get_subscription(message.from_user.id)
    if not sub:
        await message.answer(
            "You don't have an active subscription.\n"
            "Use /subscribe &lt;city&gt; &lt;HH:MM&gt; to set one up.",
            parse_mode=ParseMode.HTML,
        )
        return
    await message.answer(
        f"\u23f0 <b>Your daily subscription</b>\n"
        f"City: <b>{sub['city']}</b>\n"
        f"Time: <b>{sub['send_time']}</b> ({sub['tz']})",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Catch-all city search (must stay last among message handlers)
# ---------------------------------------------------------------------------

@router.message()
@logger.catch
async def weather_by_city(message: types.Message):
    """Returns current weather for a typed city name."""
    await _send_city_weather(message, message.text)


# ---------------------------------------------------------------------------
# Inline mode
# ---------------------------------------------------------------------------

@router.inline_query()
@logger.catch
async def inline_weather(inline_query: types.InlineQuery):
    """Handle inline queries: type @YourBot Stockholm in any chat."""
    city = inline_query.query.strip()
    if not city:
        await inline_query.answer(
            [],
            cache_time=1,
            switch_pm_text="Type a city name...",
            switch_pm_parameter="start",
        )
        return
    try:
        response = get_openweather_city_response(city)
        if str(response.get("cod")) == ERROR:
            await inline_query.answer([], cache_time=1)
            return
        weather = get_weather(response)
        text = (
            f"\U0001f324 <b>{weather.city}</b>\n"
            f"\U0001f321 {weather.temperature}\u00b0C  {feels_like_emoji(weather.feels_like)}\n"
            f"{weather.weather_type.value}\n"
            f"Feels like: {weather.feels_like}\u00b0C\n"
            f"\U0001f4a8 Wind: {weather.wind_speed} m/s\n"
            f"\U0001f4a7 Humidity: {weather.humidity}%\n"
            f"\U0001f53d Pressure: {weather.pressure} hPa"
        )
        result = InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"\U0001f324 {weather.city} \u2014 {weather.temperature}\u00b0C",
            description=f"{weather.weather_type.value}  |  Feels like {weather.feels_like}\u00b0C",
            input_message_content=InputTextMessageContent(
                message_text=text,
                parse_mode=ParseMode.HTML,
            ),
        )
        await inline_query.answer([result], cache_time=30)
    except Exception:
        await inline_query.answer([], cache_time=1)


async def main():
    sched.start(_send_subscription_weather)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
