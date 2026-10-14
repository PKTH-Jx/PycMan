from typing import Callable
from pathlib import Path

from config import GameConfig, TERMINAL_CONFIG, TURN_MS, load_config

from controller import Controller, KeyboardController, RandomController, DIRECTIONS, WAIT
from utils import Agent, Env, POINT, POWER, Player


DEFAULT_MAP = str(load_config(TERMINAL_CONFIG).map_file)


class Game:
    def __init__(self, path: str | Path | None = None,
                 player_controller: Callable[[Agent], Controller] = KeyboardController,
                 ghost_controller: Callable[[Agent], Controller] = RandomController,
                 *, config: GameConfig | None = None) -> None:
        self.config = config if config is not None else load_config(TERMINAL_CONFIG)
        self.env: Env = Env(path if path is not None else self.config.map_file, self.config)
        assert self.env.player is not None
        self.player: Player  = self.env.player
        # Factories create a separate controller (and strategy memory) per agent.
        self.controllers: dict[Agent, Controller] = {
            self.player: player_controller(self.player),
        }
        for ghost in self.env.ghosts:
            self.controllers[ghost] = ghost_controller(ghost)
        self.status = 'running'  # running, won, lost, quit
        self.check_result()

    def check_result(self) -> str:
        """Death takes priority over eating the last point in the same move."""
        if self.status != 'running':
            return self.status
        if not self.player.live:
            self.status = 'lost'
        elif not any(POINT in row or POWER in row for row in self.env.env):
            self.status = 'won'
        return self.status

    def step(self, direction: tuple[int, int] | None = None) -> str:
        """One turn: player first, then each living ghost.

        Waiting or walking into a wall still uses a turn. Eating the last point
        wins immediately if the player survives the collision at that position.
        Normally controllers supply actions. An explicit player direction is
        still accepted for tests and manual, single-step experiments.
        """
        if self.status != 'running':
            return self.status

        if direction is None:
            direction = self.controller_direction(self.player)
        if direction not in DIRECTIONS + [WAIT]:
            raise ValueError('Invalid direction')
        # The previous turn has elapsed. A new power pellet refreshes this
        # below, before collisions, so collecting it grants the full duration.
        self.player.state = max(0, self.player.state - 1)
        self.player.move(direction)
        self.env.resolve_collisions()
        if self.check_result() != 'running':
            return self.status

        for ghost in self.env.ghosts:
            if not ghost.live:
                continue
            ghost.move(self.controller_direction(ghost))
            self.env.resolve_collisions()
            if self.check_result() != 'running':
                break
        return self.status

    def controller_direction(self, agent: Agent) -> tuple[int, int]:
        controller = self.controllers[agent]
        direction = controller.get_direction()
        if direction not in DIRECTIONS + [WAIT]:
            raise ValueError(f'{type(controller).__name__} returned invalid direction: {direction!r}')
        return direction

    def run(self) -> None:
        """Keyboard-driven terminal demo, using one action per entered command."""
        keyboard = KeyboardController(self.player, continuous=False)
        self.controllers[self.player] = keyboard
        print('W/A/S/D + Enter: move | Enter: wait | Q: quit')
        self.env.print()
        print(f'Score: {self.player.score}')
        while self.status == 'running':
            try:
                command = input('Move: ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                self.status = 'quit'
                break
            if command == 'q':
                self.status = 'quit'
                break
            if not keyboard.handle_key(command):
                print('Use W, A, S, D, Enter or Q.')
                continue
            self.step()
            self.env.print()
            print(f'Score: {self.player.score}')
            if self.player.state:
                print(f'Power: {self.player.state} turns remaining')

        messages = {'won': 'You win!', 'lost': 'Game over!', 'quit': 'Goodbye!'}
        print(messages[self.status])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the terminal game')
    parser.add_argument('--config', default=TERMINAL_CONFIG, help='Path to a map JSON profile')
    args = parser.parse_args()
    Game(config=load_config(args.config)).run()
