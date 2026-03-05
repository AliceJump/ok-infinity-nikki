from enum import Enum

class HSVRange(tuple, Enum):
    WHITE = (((0, 0, 200), (180, 50, 255)),)
    GOLD_TEXT = (
        ((18, 120, 170), (40, 255, 255)),
        ((18, 60, 140), (45, 200, 255)),
    )
    DARK_GRAY_TEXT = (
        ((0, 0, 40), (180, 30, 90)),
    )
