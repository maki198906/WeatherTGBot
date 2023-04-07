# import logging
import os
import time

from loguru import logger
from aiogram import Bot, Dispatcher, executor, types

from weather_api_service import (get_openweather_response, get_weather, get_openweather_city_response,
                                 Coordinates, ERROR, get_coordinates_by_city, get_openweather_air_response,
                                 get_air_quality_type, get_weather_random)
from timezoneutils import timezone, sun_condition
from weather_repr import weather_repr, weather_repr_city, weather_repr_random
from exceptions import WrongInput
from random_weather import generate_random_coords

# initialize logging file to catch errors
logger.add("log_errors.log", format="{time} {level} {message}",
           rotation="5 MB", compression="zip")

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

# initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Returns info what bot is about"""
    await message.answer("Hi!\nI'm <b>WeWeather</b> Bot\n"
                         "I can provide you with the weather around you or more\n"
                         "Just type the city you are looking for\n"
                         "or type /inplace so the weather around you pops up.\n"
                         "If you'd like to explore the weather at random spot type /random",
                         parse_mode=types.ParseMode.HTML)


def get_keyboard():
    """Initiates button to share with GEO"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder='Share GEO or Discard')
    button1 = types.KeyboardButton("🌍 Share GEO", request_location=True)
    button2 = types.KeyboardButton("🚫 Discard")
    keyboard.add(button1, button2)
    return keyboard


@dp.message_handler(lambda message: message.text == "🚫 Discard")
async def discard(message: types.Message):
    await message.answer("Ok pal, I got it!", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['random'])
async def random_weather(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Click",
        callback_data="random_weather")
    )
    await message.answer('To explore random weather just for fun click me', reply_markup=keyboard)


@dp.callback_query_handler(text='random_weather')
async def send_random_weather(callback: types.CallbackQuery):
    coordinates = generate_random_coords()
    openweather_response = get_openweather_response(coordinates.latitude, coordinates.longitude)
    air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
    air_index_quality = get_air_quality_type(air_index_response)
    weather = get_weather_random(openweather_response)
    sun_conditions = sun_condition(sunrise=time.mktime(weather.sunrise.timetuple()),
                                   sunset=time.mktime(weather.sunset.timetuple()),
                                   coordinates=coordinates)
    area, local_time = timezone(coordinates)
    weather_represent = weather_repr_random(weather)
    await callback.message.answer(f"Time zone: {area}\n"
                                  f"Local time: {local_time}\n"
                                  f"Air Index Quality: {air_index_quality.value}\n"
                                  f"{'*' * 10}\n"
                                  f"{weather_represent}"
                                  f"{'*' * 10}\n"
                                  f"🌅: {sun_conditions.sunrise.strftime('%H:%M')}\n"
                                  f"🌇: {sun_conditions.sunset.strftime('%H:%M')}",
                                  parse_mode=types.ParseMode.HTML)
    await callback.message.answer_location(latitude=coordinates.latitude, longitude=coordinates.longitude)
    await callback.answer()


@dp.message_handler(content_types=['location'])
async def weather_by_location(message: types.Message):
    """Returns readable format of the weather """
    lat = message.location.latitude
    lon = message.location.longitude
    coordinates = Coordinates(*map(lambda x: round(x, 2), [lat, lon]))
    openweather_response = get_openweather_response(coordinates.latitude, coordinates.longitude)
    air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
    weather = get_weather(openweather_response)
    air_index_quality = get_air_quality_type(air_index_response)
    sun_conditions = sun_condition(sunrise=time.mktime(weather.sunrise.timetuple()),
                                   sunset=time.mktime(weather.sunset.timetuple()),
                                   coordinates=coordinates)
    area, local_time = timezone(coordinates)
    weather_represent = weather_repr(weather)

    await message.answer(f"Time zone: {area}\n"
                         f"Local time: {local_time}\n"
                         f"Air Index Quality: {air_index_quality.value}\n"
                         f"{'*' * 10}\n"
                         f"{weather_represent}"
                         f"{'*' * 10}\n"
                         f"🌅: {sun_conditions.sunrise.strftime('%H:%M')}\n"
                         f"🌇: {sun_conditions.sunset.strftime('%H:%M')}",
                         reply_markup=types.ReplyKeyboardRemove(),
                         parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands=['inplace'])
async def weather_me(message: types.Message):
    """Invokes the button in Telegram"""
    reply = "Click on the button below to share your location"
    await message.answer(reply, reply_markup=get_keyboard())


@dp.message_handler()
@logger.catch
async def weather_by_city(message: types.Message):
    """Represents weather in Telegram"""
    openweather_city_response = get_openweather_city_response(message.text)
    if openweather_city_response['cod'] != ERROR:
        coordinates = get_coordinates_by_city(openweather_city_response)
        air_index_response = get_openweather_air_response(coordinates.latitude, coordinates.longitude)
        air_index_quality = get_air_quality_type(air_index_response)
        area, local_time = timezone(coordinates)
        weather = get_weather(openweather_city_response)
        sun_conditions = sun_condition(sunrise=time.mktime(weather.sunrise.timetuple()),
                                       sunset=time.mktime(weather.sunset.timetuple()),
                                       coordinates=coordinates)
        weather_represent = weather_repr_city(weather)
        await message.answer(f"Time zone: {area}\n"
                             f"Local time: {local_time}\n"
                             f"Air Index Quality: {air_index_quality.value}\n"
                             f"{'*' * 10}\n"
                             f"{weather_represent}"
                             f"{'*' * 10}\n"
                             f"🌅: {sun_conditions.sunrise.strftime('%H:%M')}\n"
                             f"🌇: {sun_conditions.sunset.strftime('%H:%M')}")
        await bot.send_location(message.chat.id, latitude=coordinates.latitude, longitude=coordinates.longitude)
    else:
        await message.answer('Oops, looks like there is no such city\n'
                             'Check the spelling')
        raise WrongInput(f'City "{message.text}" is not defined')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
