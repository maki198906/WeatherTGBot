# import logging
import os
import time

from dotenv import load_dotenv
from loguru import logger
from aiogram import Bot, Dispatcher, executor, types

from weather_api_service import (get_openweather_response, get_weather, get_openweather_city_response,
                                 Coordinates, ERROR, get_coordinates_by_city)
from timezoneutils import timezone, sun_condition
from weather_repr import weather_repr, weather_repr_city
from exceptions import WrongInput

# initialize logging file to catch errors
logger.add("log_errors.log", format="{time} {level} {message}",
           rotation="5 MB", compression="zip")

# import a .env file into a Python application
load_dotenv()

API_TOKEN = os.environ["TELEGRAM_API_TOKEN"]

# initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Returns info what bot is about"""
    await message.answer("Hi!\nI'm <b>WeWeather</b> Bot\n"
                         "I can provide you with the weather around you or more\n"
                         "Just type the city you are looking for\n"
                         "or type /inplace so the weather around you pops up",
                         parse_mode=types.ParseMode.HTML)


def get_keyboard():
    """Initiates button to share with GEO"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("🌍 Share with GEO", request_location=True)
    keyboard.add(button)
    return keyboard


@dp.message_handler(content_types=['location'])
async def weather_by_location(message: types.Message):
    """Returns readable format of the weather """
    lat = message.location.latitude
    lon = message.location.longitude
    coordinates = Coordinates(*map(lambda x: round(x, 2), [lat, lon]))
    openweather_response = get_openweather_response(coordinates.latitude, coordinates.longitude)
    weather = get_weather(openweather_response)
    sun_conditions = sun_condition(sunrise=time.mktime(weather.sunrise.timetuple()),
                                   sunset=time.mktime(weather.sunset.timetuple()),
                                   coordinates=coordinates)
    area, local_time = timezone(coordinates)
    weather_represent = weather_repr(weather)

    await message.answer(f"Time zone {area}\n"
                         f"Local time {local_time}\n"
                         f"{'*' * 10}\n"
                         f"{weather_represent}"
                         f"Sunrise {sun_conditions.sunrise.strftime('%H:%M')}\n"
                         f"Sunset {sun_conditions.sunset.strftime('%H:%M')}",
                         reply_markup=types.ReplyKeyboardRemove())


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
        area, local_time = timezone(coordinates)
        weather = get_weather(openweather_city_response)
        sun_conditions = sun_condition(sunrise=time.mktime(weather.sunrise.timetuple()),
                                       sunset=time.mktime(weather.sunset.timetuple()),
                                       coordinates=coordinates)
        weather_represent = weather_repr_city(weather)
        await message.answer(f"Time zone {area}\n"
                             f"Local time {local_time}\n"
                             f"{'*' * 10}\n"
                             f"{weather_represent}\n"
                             f"Sunrise {sun_conditions.sunrise.strftime('%H:%M')}\n"
                             f"Sunset {sun_conditions.sunset.strftime('%H:%M')}")
    else:
        await message.answer('Oops, looks like there is no such city\n'
                             'Check the spelling')
        raise WrongInput(f'City "{message.text}" is not defined')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
