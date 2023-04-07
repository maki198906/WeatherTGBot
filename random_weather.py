import random
from decimal import Decimal
from typing import NamedTuple


class Coordinates(NamedTuple):
    latitude: float
    longitude: float


ACCURACY = Decimal('.0001')


def generate_random_coords() -> Coordinates:
    """
    Generates a random set of longitude and latitude coordinates
    """
    # Set the range of longitude and latitude values
    min_longitude, max_longitude = -180, 180
    min_latitude, max_latitude = -90, 90

    # Generate random longitude and latitude values within the given range
    longitude = Decimal(random.uniform(min_longitude, max_longitude)).quantize(ACCURACY)
    latitude = Decimal(random.uniform(min_latitude, max_latitude)).quantize(ACCURACY)

    return Coordinates(latitude=float(latitude), longitude=float(longitude))
