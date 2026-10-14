import os
from pathlib import Path

from codebook import AGENT, CODEBOOK, GHOST, PLAYER, POINT, POWER, ROAD, WALL
from config import DEFAULT_SETTINGS, GameConfig

# Agent Score
GET_POINT = DEFAULT_SETTINGS.get_point
BEAT_GHOST = DEFAULT_SETTINGS.beat_ghost
GET_POWER = DEFAULT_SETTINGS.get_power
POWER_TURNS = DEFAULT_SETTINGS.power_turns

class Env:
    def __init__(self, path: str | Path, config: GameConfig = DEFAULT_SETTINGS) -> None:
        self.config = config
        assert os.path.exists(path=path)
        with open(file=path, mode='r', encoding='utf-8') as f:
            _env: list[str] = f.readlines()
        _env = [_row.rstrip('\r\n') for _row in _env]
        if not _env or not _env[0]:
            raise ValueError('Map must not be empty')
        self.rows:int = len(_env)
        self.cols:int = len(_env[0])
        self.codebook:dict[str, int] = CODEBOOK.copy()
        self._rev:dict[int,str] = {v:k for k,v in self.codebook.items()}

        self.env: list[list[int]] = []
        for row in _env:
            if len(row) != self.cols:
                raise ValueError('Map rows must have the same width')
            self.env.append([self.codebook[_s] for _s in row])

        self.player:Player|None = None
        self.ghosts:list[Ghost] = []
        self.agentRegistration() # register Agents


    def assert_env(self)->None:
        """
        assert the environment is all right
        """
        assert len(self.env) == self.rows
        for row in self.env:
            assert len(row) == self.cols

    def get_tile(self, x: int, y: int) -> int:
        """Coordinates are (x, y): right and down; storage is [row][column]."""
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            raise IndexError('Tile coordinates are outside the map')
        return self.env[y][x]

    def set_tile(self, x: int, y: int, value: int) -> None:
        """Store terrain/items only. Characters keep their own positions."""
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            raise IndexError('Tile coordinates are outside the map')
        if value not in (ROAD, WALL, POINT, POWER):
            raise ValueError('A tile must be ROAD, WALL, POINT or POWER')
        self.env[y][x] = value

    def can_walk(self, x: int, y: int) -> bool:
        return (
            0 <= x < self.cols
            and 0 <= y < self.rows
            and self.get_tile(x, y) != WALL
        )

    def update_element(self, x: int, y: int, _type: int) -> None:
        """Compatibility wrapper for existing callers."""
        self.set_tile(x, y, _type)

    def print(self) -> None:
        """Overlay living characters on a temporary display, not on the map."""
        display = [[self._rev[tile] for tile in row] for row in self.env]
        for ghost in self.ghosts:
            if ghost.live:
                display[ghost.y][ghost.x] = ghost.code
        if self.player is not None and self.player.live:
            display[self.player.y][self.player.x] = self.player.code
        for row in display:
            print(''.join(row))

    def agentRegistration(self) -> None:
        """Convert spawn markers into characters standing on ROAD tiles."""
        for y, row in enumerate(self.env):
            for x, element in enumerate(row):
                if element == PLAYER:
                    if self.player is not None:
                        raise ValueError('Map must contain exactly one player')
                    self.player = Player(x, y, self)
                    self.set_tile(x, y, ROAD)
                elif element == GHOST:
                    self.ghosts.append(Ghost(x, y, self))
                    self.set_tile(x, y, ROAD)
                elif element == AGENT:
                    raise ValueError('Use c or g instead of the generic a marker')
        if self.player is None:
            raise ValueError('Map must contain exactly one player')

    def resolve_collisions(self) -> None:
        """
        Movement itself only changes positions/items.
        Keep collision rules here until Game owns the update loop.
        """
        player = self.player
        if player is None or not player.live:
            # No player, or already dead, so no collisions to resolve.
            return
        for ghost in self.ghosts:
            if ghost.live and (player.x, player.y) == (ghost.x, ghost.y):
                if player.state > 0:
                    # Beat Success
                    ghost.live = False
                    player.score += self.config.beat_ghost
                else:
                    # Be eaten by Ghost
                    player.score = 0
                    player.live = False
                    return


class Agent:
    def __init__(self, x:int, y: int, env: Env) -> None:
        self.x:int = x
        self.y:int = y
        self.env:Env = env # help moving
        self.code:str = 'a'
        self.live:bool = True

    def getItem(self, pos: tuple[int, int]) -> int:
        """Read terrain/items; characters are not stored in tiles."""
        x, y = pos
        return self.env.get_tile(x, y)

    def moveForward(self, future_pos: tuple[int, int]) -> None:
        """Update position only; move() checks the destination first."""
        self.x, self.y = future_pos

    def move(self, direction: tuple[int, int]) -> bool:
        """Move one tile. Return False for waiting, walls or map boundaries."""
        if direction not in [(1, 0), (0, 1), (-1, 0), (0, -1), (0, 0)]:
            raise ValueError('Invalid direction')
        if not self.live or direction == (0, 0):
            return False
        dx, dy = direction
        future_pos = (self.x + dx, self.y + dy)
        if not self.env.can_walk(*future_pos):
            return False
        self.moveForward(future_pos)
        return True


class Player(Agent):
    def __init__(self, x: int, y: int, env: Env) -> None:
        super().__init__(x, y, env)
        self.code: str = 'c'
        self.state: int = 0  # Remaining powered turns; 0 means normal.
        self.score: int = 0

    def move(self, direction: tuple[int, int]) -> bool:
        if not super().move(direction):
            return False
        tile = self.env.get_tile(self.x, self.y)
        if tile == POINT:
            self.env.set_tile(self.x, self.y, ROAD)
            self.score += self.env.config.get_point
        elif tile == POWER:
            self.env.set_tile(self.x, self.y, ROAD)
            self.score += self.env.config.get_power
            self.state = self.env.config.power_turns
        return True


class Ghost(Agent):
    def __init__(self, x: int, y: int, env: Env) -> None:
        super().__init__(x, y, env)
        self.code: str = 'g'
        # Inherit Agent.move
