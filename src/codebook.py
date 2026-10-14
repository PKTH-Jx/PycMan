"""Tile identifiers and the characters used in text maps."""

ROAD = 0
WALL = 1
POINT = 2
PLAYER = 3
GHOST = 4
AGENT = 5
POWER = 6

CODEBOOK: dict[str, int] = {
    ' ': ROAD,
    '#': WALL,
    '.': POINT,
    'o': POWER,
    'c': PLAYER,
    'g': GHOST,
    'a': AGENT,
}
