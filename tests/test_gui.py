import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pygame
from gui import GUI, TURN_MS, FLASH_TURNS, FLASH_INTERVAL
from utils import WALL, POINT, POWER, POWER_TURNS
from controller import Controller


class GUITest(unittest.TestCase):
    def setUp(self):
        self.gui = GUI()

    def tearDown(self):
        pygame.quit()

    def key(self, key):
        self.gui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_map_reachable(self):
        env = self.gui.game.env
        reached = {(env.player.x, env.player.y)}
        pending = list(reached)
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

    def test_start_move_pause_restart(self):
        self.gui.update(TURN_MS)
        self.assertEqual(self.gui.game.player.x, 1)
        self.key(pygame.K_RIGHT)
        self.gui.update(TURN_MS)
        self.assertEqual(self.gui.game.player.x, 2)
        self.assertEqual(self.gui.game.player.score, 10)
        self.key(pygame.K_SPACE)
        self.gui.update(TURN_MS)
        self.assertEqual(self.gui.game.player.x, 2)
        self.key(pygame.K_SPACE)
        self.gui.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertTrue(self.gui.paused)
        self.key(pygame.K_r)
        self.assertTrue(self.gui.started)
        self.assertEqual(self.gui.game.player.score, 0)

    def test_buffered_turn(self):
        self.key(pygame.K_RIGHT)
        self.gui.update(TURN_MS)
        self.key(pygame.K_DOWN)  # Row 2 is blocked until column 5.
        for _ in range(4):
            self.gui.update(TURN_MS)
        player = self.gui.game.player
        self.assertEqual((player.x, player.y), (5, 2))

    def test_render_states_and_terminal_freeze(self):
        env = self.gui.game.env
        before = [row[:] for row in env.env]
        self.gui.draw()
        self.gui.started = True
        self.gui.draw()
        self.gui.paused = True
        self.gui.draw()
        self.gui.paused = False
        for status in ('won', 'lost'):
            self.gui.game.status = status
            self.gui.draw()
            with patch.object(self.gui.game, 'step') as step:
                self.gui.update(TURN_MS)
                step.assert_not_called()
        self.assertEqual(before, env.env)
        for sprite in self.gui.sprites.values():
            self.assertEqual(sprite.get_at((0, 0)).a, 0)
            self.assertGreater(sprite.get_at((20, 20)).a, 0)

    def test_restart_in_all_states(self):
        for status in ('running', 'won', 'lost'):
            with self.subTest(status=status):
                self.gui.game.player.move((1, 0))
                self.gui.game.player.state = 12
                self.gui.game.player.live = False
                self.gui.game.env.ghosts[0].live = False
                self.gui.game.status = status
                self.gui.paused = True
                old_game = self.gui.game
                self.key(pygame.K_r)
                self.assertIsNot(old_game, self.gui.game)
                self.assertEqual(self.gui.game.status, 'running')
                self.assertEqual(self.gui.game.player.state, 0)
                self.assertTrue(self.gui.game.player.live)
                self.assertTrue(all(g.live for g in self.gui.game.env.ghosts))
                self.assertEqual(self.gui.game.env.get_tile(3, 1), POWER)
                self.assertFalse(self.gui.paused)
                self.assertTrue(self.gui.started)
                self.gui.update(TURN_MS)
                self.assertEqual(self.gui.game.player.x, 2)

    def test_restart_scancode_and_mouse(self):
        self.gui.game.player.score = 123
        self.gui.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_UNKNOWN, scancode=pygame.KSCAN_R))
        self.assertEqual(self.gui.game.player.score, 0)
        self.gui.game.player.score = 123
        self.gui.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=self.gui.restart_button.center))
        self.assertEqual(self.gui.game.player.score, 0)
        self.assertTrue(self.gui.started)

    def test_power_timer_and_pause(self):
        self.key(pygame.K_RIGHT)
        self.gui.update(TURN_MS)
        self.gui.update(TURN_MS)
        self.assertEqual(self.gui.game.player.state, POWER_TURNS)
        self.gui.draw()
        self.key(pygame.K_SPACE)
        self.gui.update(10000)
        self.assertEqual(self.gui.game.player.state, POWER_TURNS)
        self.key(pygame.K_SPACE)
        self.gui.update(TURN_MS)
        self.assertEqual(self.gui.game.player.state, POWER_TURNS - 1)

    def test_custom_strategy_survives_restart_with_fresh_state(self):
        class StudentController(Controller):
            def __init__(self, agent):
                super().__init__(agent)
                self.calls = 0

            def get_direction(self):
                self.calls += 1
                return (1, 0)

        self.gui = GUI(player_controller=StudentController)
        self.assertTrue(self.gui.started)
        self.gui.update(TURN_MS)
        original = self.gui.player_controller
        self.assertEqual(original.calls, 1)
        self.assertEqual(self.gui.game.player.x, 2)
        self.key(pygame.K_r)
        self.assertIsInstance(self.gui.player_controller, StudentController)
        self.assertIsNot(self.gui.player_controller, original)
        self.assertEqual(self.gui.player_controller.calls, 0)
        self.assertIs(self.gui.player_controller.agent, self.gui.game.player)
        self.gui.update(TURN_MS)
        self.assertEqual(self.gui.game.player.x, 2)

    def test_close(self):
        self.gui.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.gui.running)

    def test_frightened_colors_follow_game_timer(self):
        cases = [(0, 'ghost'), (POWER_TURNS, 'ghost_blue'),
                 (FLASH_TURNS + 1, 'ghost_blue'), (FLASH_TURNS, 'ghost_blue'),
                 (FLASH_TURNS - FLASH_INTERVAL, 'ghost_white'),
                 (FLASH_TURNS - 2 * FLASH_INTERVAL, 'ghost_blue'),
                 (1, 'ghost_white'), (0, 'ghost')]
        for turns, name in cases:
            with self.subTest(turns=turns):
                self.gui.game.player.state = turns
                self.assertIs(self.gui.ghost_sprite(), self.gui.sprites[name])
                self.gui.draw()
        self.gui.started = True
        self.gui.paused = True
        self.gui.game.player.state = FLASH_TURNS - FLASH_INTERVAL
        self.gui.update(10000)
        self.assertIs(self.gui.ghost_sprite(), self.gui.sprites['ghost_white'])


if __name__ == '__main__':
    unittest.main()
