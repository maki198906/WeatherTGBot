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

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


def _map_button(lat: float, lon: float) -> types.InlineKeyboardMarkup:
    """Inline keyboard with a direct link to the OpenWeatherMap map."""
    url = (
        f"https://openweathermap.org/weathermap?"
        f"basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=10"
    )
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="\U0001f5fa View on map", url=url)]]
    )


@router.message(Command("start", "help"))
async def send_welcome(message: types.Message):
    """Returns info about what the bot can do."""
    await message.answer(
        "Hi!\nI'm <b>WeWeather</b> Bot\n"
        "I can provide you with the weather around you or more\n\n"
        "\U0001f4cd Just type a city name to get current weather\n"
        "\U0001f4c5 Use /forecast &lt;city&gt; for a 5-day forecast\n"
        "\U0001f4cc Use /inplace to share your location\n"
        "\U0001f3b2 Use /random for weather at a random spot",
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


@router.message()
@logger.catch
async def weather_by_city(message: types.Message):
    """Returns current weather for a typed city name."""
    openweather_city_response = get_openweather_city_response(message.text)
    if openweather_city_response["cod"] != ERROR:
        coordinates = get_coordinates_by_city(openweather_city_response)
        air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
        air_index_quality = get_air_quality_type(air_index_response)
        area, local_time = timezone(coordinates)
        weather = get_weather(openweather_city_response)
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
        raise WrongInput(f'City "{message.text}" is not defined')


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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
