import timezonefinder
import pytz

from weather_api_service import Coordinates
from typing import NamedTuple
from datetime import datetime


class SunTime(NamedTuple):
    sunset: datetime
    sunrise: datetime


def timezone(coordinates: Coordinates) -> [str, str]:
    """Returns Area and Local Time"""
    tf = timezonefinder.TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lat=coordinates.latitude, lng=coordinates.longitude)
    fmt = '%H:%M'
    if timezone_str:
        cur_timezone = pytz.timezone(timezone_str)
        dt = datetime.utcnow()
        # method utcoffset() returns the UTC offset for a timezone instance
        local_time = dt + cur_timezone.utcoffset(dt)
        local_time = local_time.strftime(fmt)
        return timezone_str.split('/')[0], local_time
    else:
        return


def sun_condition(sunrise: float, sunset: float, coordinates: Coordinates) -> SunTime:
    """Returns sunrise&sunset regarding the city requested (local time)"""
    tf = timezonefinder.TimezoneFinder()
    timezone_str = tf.certain_timezone_at(lat=coordinates.latitude, lng=coordinates.longitude)
    cur_timezone = pytz.timezone(timezone_str)
    utc_time_sunrise = datetime.utcfromtimestamp(sunrise)
    utc_time_sunset = datetime.utcfromtimestamp(sunset)
    certain_time_sunrise = utc_time_sunrise.replace(tzinfo=pytz.utc).astimezone(cur_timezone)
    certain_time_sunset = utc_time_sunset.replace(tzinfo=pytz.utc).astimezone(cur_timezone)
    sun_conditions = SunTime(sunset=certain_time_sunset, sunrise=certain_time_sunrise)
    return sun_conditions
