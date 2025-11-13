import pytest
from utils.render import calculate_position, render_video
import config
import os

def test_calculate_position_valid():
    assert calculate_position("top left", 1920, 1080, 200, 100) == (27.0, 27.0)
    assert calculate_position("top right", 1920, 1080, 200, 100) == (1693.0, 27.0)
    assert calculate_position("bottom left", 1920, 1080, 200, 100) == (27.0, 953.0)
    assert calculate_position("bottom right", 1920, 1080, 200, 100) == (1693.0, 953.0)

def test_calculate_position_invalid():
    with pytest.raises(ValueError):
        calculate_position("invalid", 1920, 1080, 200, 100)
