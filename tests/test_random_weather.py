import sys
import os
from decimal import Decimal
from random_weather import generate_random_coords, Coordinates

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_generate_random_coords():
    # Generate 10 sets of coordinates and check that they are within the expected range
    for _ in range(10):
        coords = generate_random_coords()
        assert isinstance(coords, Coordinates)
        assert -90 <= coords.latitude <= 90
        assert -180 <= coords.longitude <= 180
        assert isinstance(coords.latitude, float)
        assert isinstance(coords.longitude, float)
        assert isinstance(coords.latitude, Decimal) is False
        assert isinstance(coords.longitude, Decimal) is False
