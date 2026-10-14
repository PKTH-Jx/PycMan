"""Validate playable layouts and exercise small, reusable map fixtures."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import sys
import unittest
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from codebook import POINT, POWER, WALL
from config import load_config
from controller import Controller, KeyboardController, WAIT
from game import Game

FIXTURES = ROOT / 'tests/maps'


class WaitController(Controller):
    def get_direction(self):
        return WAIT


def fixture(name):
    return Game(FIXTURES / f'{name}.txt', ghost_controller=WaitController)


class MapTest(unittest.TestCase):
    def test_playable_maps_are_connected_and_can_be_cleared(self):
        profiles = sorted((ROOT / 'configs').glob('*.json'))
        profiles = [path for path in profiles if path.name != 'defaults.json']
        self.assertGreaterEqual(len(profiles), 5)
        for profile in profiles:
            with self.subTest(profile=profile.name):
                config = load_config(profile)
                game = Game(config=config)
                env = game.env
                source = config.map_file.read_text()
                self.assertEqual(source.count('c'), 1)
                self.assertEqual(len(env.ghosts), source.count('g'))
                self.assertEqual(game.status, 'running')
                self.assertTrue(all(tile == WALL for tile in env.env[0] + env.env[-1]))
                self.assertTrue(all(row[0] == row[-1] == WALL for row in env.env))
                start = (game.player.x, game.player.y)
                reached = {start}
                pending = [start]
                while pending:
                    x, y = pending.pop()
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        pos = x + dx, y + dy
                        if pos not in reached and env.can_walk(*pos):
                            reached.add(pos)
                            pending.append(pos)
                floor = {(x, y) for y, row in enumerate(env.env)
                         for x, tile in enumerate(row) if tile != WALL}
                self.assertEqual(reached, floor)

                # Disable opponents to verify every collectible can be cleared.
                for ghost in env.ghosts:
                    ghost.live = False
                expected_score = sum(row.count(POINT) * config.get_point
                                     + row.count(POWER) * config.get_power for row in env.env)
                while game.status == 'running':
                    queue = deque([((game.player.x, game.player.y), [])])
                    visited = {(game.player.x, game.player.y)}
                    route = None
                    while queue:
                        (x, y), steps = queue.popleft()
                        if env.get_tile(x, y) in (POINT, POWER):
                            route = steps
                            break
                        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                            pos = x + dx, y + dy
                            if pos not in visited and env.can_walk(*pos):
                                visited.add(pos)
                                queue.append((pos, steps + [(dx, dy)]))
                    self.assertIsNotNone(route, 'No route to remaining collectibles')
                    for direction in route:
                        game.step(direction)
                self.assertEqual(game.status, 'won')
                self.assertEqual(game.player.score, expected_score)
                fresh = Game(config=config)
                self.assertEqual(fresh.status, 'running')
                self.assertEqual(fresh.player.score, 0)

    def test_playable_maps_render_and_restart(self):
        import pygame
        from gui import GUI

        self.addCleanup(pygame.quit)
        for name in ('training', 'crossroads', 'labyrinth'):
            with self.subTest(map=name):
                gui = GUI(config=load_config(ROOT / f'configs/{name}.json'))
                gui.draw()
                self.assertGreaterEqual(gui.width, gui.game.env.cols * 40)
                old_game = gui.game
                gui.restart()
                self.assertIsNot(gui.game, old_game)
                self.assertEqual(gui.game.status, 'running')
                gui.draw()

    def test_corridor_can_be_won(self):
        game = fixture('corridor')
        for _ in range(3):
            game.step((1, 0))
        self.assertEqual(game.status, 'won')
        self.assertEqual(game.player.score, 3 * game.config.get_point)

    def test_power_allows_collision_and_preserves_other_dots(self):
        game = fixture('power_collision')
        game.step((1, 0))
        self.assertEqual(game.player.state, game.config.power_turns)
        game.step((1, 0))
        game.step((1, 0))
        self.assertFalse(game.env.ghosts[0].live)
        self.assertTrue(game.player.live)
        self.assertEqual(game.status, 'running')
        self.assertEqual(game.player.score, game.config.get_power + game.config.get_point
                         + game.config.beat_ghost)

    def test_unpowered_collision_loses(self):
        game = fixture('collision')
        self.assertEqual(game.step((1, 0)), 'lost')
        self.assertFalse(game.player.live)

    def test_junction_buffers_turn(self):
        game = fixture('junction')
        keyboard = game.controllers[game.player]
        self.assertIsInstance(keyboard, KeyboardController)
        keyboard.handle_key('right')
        game.step()
        keyboard.handle_key('down')
        game.step()
        self.assertEqual((game.player.x, game.player.y), (3, 1))
        game.step()
        self.assertEqual((game.player.x, game.player.y), (3, 2))

    def test_open_boundaries_block_out_of_range_movement(self):
        game = fixture('open_boundary')
        for direction in [(-1, 0), (0, -1), (0, 1)]:
            self.assertFalse(game.player.move(direction))
        self.assertEqual((game.player.x, game.player.y), (0, 0))
        game.player.move((1, 0))
        game.player.move((1, 0))
        self.assertFalse(game.player.move((1, 0)))

    def test_invalid_layouts_are_rejected(self):
        for name, message in [('invalid_ragged', 'same width'),
                              ('invalid_two_players', 'exactly one player'),
                              ('invalid_no_player', 'exactly one player')]:
            with self.subTest(map=name), self.assertRaisesRegex(ValueError, message):
                fixture(name)


if __name__ == '__main__':
    unittest.main()
