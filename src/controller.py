"""Controllers choose directions; they must not move agents or change the map.

No pygame dependency: key names arrive from the GUI or terminal as strings.
"""
import random

from utils import Agent

DIRECTIONS = [(1, 0), (0, 1), (-1, 0), (0, -1)]
WAIT = (0, 0)


class Controller:
    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    def get_direction(self) -> tuple[int, int]:
        """Return one cardinal step or (0, 0) to wait. Override in a strategy."""
        raise NotImplementedError

    def handle_key(self, key: str) -> bool:
        """Return True if a movement key was accepted; AI ignores keys."""
        return False

    def legal_directions(self) -> list[tuple[int, int]]:
        agent = self.agent
        return [(dx, dy) for dx, dy in DIRECTIONS
                if agent.env.can_walk(agent.x + dx, agent.y + dy)]


class KeyboardController(Controller):
    KEYS = {
        'left': (-1, 0), 'a': (-1, 0),
        'right': (1, 0), 'd': (1, 0),
        'up': (0, -1), 'w': (0, -1),
        'down': (0, 1), 's': (0, 1), '': WAIT,
    }

    def __init__(self, agent: Agent, continuous: bool = True) -> None:
        super().__init__(agent)
        self.continuous: bool = continuous
        self.direction: tuple[int, int] = WAIT
        self.pending: tuple[int, int] = WAIT

    def handle_key(self, key: str) -> bool:
        key = key.lower()
        if key not in self.KEYS:
            return False
        self.pending = self.KEYS[key]
        return True

    def get_direction(self) -> tuple[int, int]:
        if not self.continuous:
            # Terminal: each entered command is exactly one requested action.
            direction = self.pending
            self.pending = WAIT
            return direction
        # GUI: keep moving, buffering a requested turn until a junction opens.
        if self.pending == WAIT or self.pending in self.legal_directions():
            self.direction = self.pending
        return self.direction


class RandomController(Controller):
    def get_direction(self) -> tuple[int, int]:
        choices = self.legal_directions()
        return random.choice(choices) if choices else WAIT

class BFSController(Controller):
    ...

class DFSController(Controller):
    ...

class AStarController(Controller):
    ...
