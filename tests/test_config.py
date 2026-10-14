import json
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from config import load_config
from controller import Controller, WAIT
from game import Game


class WaitController(Controller):
    def get_direction(self):
        return WAIT


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'map.txt').write_text('########\n#c.og .#\n########\n')
        self.profile = self.root / 'custom.json'

    def config(self, **overrides):
        self.profile.write_text(json.dumps({'map_file': 'map.txt', **overrides}))
        return load_config(self.profile)

    def test_relative_map_and_inherited_defaults(self):
        config = self.config(turn_ms=90)
        self.assertEqual(config.map_file, self.root / 'map.txt')
        self.assertEqual(config.turn_ms, 90)
        self.assertEqual(config.get_point, 10)
        self.assertEqual(Game(config=config).env.cols, 8)

    def test_custom_rules_and_independent_games(self):
        config = self.config(get_point=7, get_power=13, beat_ghost=19,
                             power_turns=8, flash_turns=4)
        custom = Game(config=config, ghost_controller=WaitController)
        normal = Game(path=config.map_file, ghost_controller=WaitController)
        custom.step((1, 0))
        self.assertEqual(custom.player.score, 7)
        custom.step((1, 0))
        self.assertEqual(custom.player.state, 8)
        self.assertEqual(custom.player.score, 20)
        custom.step((1, 0))
        self.assertEqual(custom.player.score, 39)
        self.assertFalse(custom.env.ghosts[0].live)
        for _ in range(7):
            custom.step(WAIT)
        self.assertEqual(custom.player.state, 0)
        normal.step((1, 0))
        normal.step((1, 0))
        self.assertEqual(normal.player.score, 60)
        self.assertEqual(normal.player.state, 40)

    def test_invalid_settings(self):
        for override in ({'turn_ms': 0}, {'power_turns': True}, {'get_point': -1},
                         {'flash_interval': 0}, {'power_turns': 5},
                         {'turn_mss': 90}, {'game_config': ''}, {'game_config': 5}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.config(**override)
        self.profile.write_text('[]')
        with self.assertRaisesRegex(ValueError, 'JSON object'):
            load_config(self.profile)

    def test_referenced_game_config_and_profile_overrides(self):
        shared = self.root / 'rules'
        shared.mkdir()
        settings = {
            'turn_ms': 100, 'get_point': 3, 'get_power': 15, 'beat_ghost': 25,
            'power_turns': 20, 'flash_turns': 6, 'flash_interval': 1,
        }
        (shared / 'game.json').write_text(json.dumps(settings))
        config = self.config(game_config='rules/game.json', turn_ms=80)
        self.assertEqual(config.turn_ms, 80)
        self.assertEqual(config.power_turns, 20)
        self.assertEqual(config.get_point, 3)
        self.assertEqual(config.map_file, self.root / 'map.txt')
        game = Game(config=config, ghost_controller=WaitController)
        game.step((1, 0))
        self.assertEqual(game.player.score, 3)

    def test_missing_referenced_config_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            self.config(game_config='missing.json')

    def test_explicit_map_overrides_profile_map(self):
        config = self.config()
        other = self.root / 'other.txt'
        other.write_text('#####\n#c..#\n#####\n')
        self.assertEqual(Game(other, config=config).env.cols, 5)

    def test_gui_uses_profile_for_timing_display_and_restart(self):
        import pygame
        from gui import GUI

        self.addCleanup(pygame.quit)
        config = self.config(turn_ms=90, power_turns=8, flash_turns=4, flash_interval=1)
        gui = GUI(config=config, ghost_controller=WaitController)
        gui.player_controller.handle_key('right')
        gui.started = True
        gui.update(89)
        self.assertEqual(gui.game.player.x, 1)
        gui.update(1)
        self.assertEqual(gui.game.player.x, 2)
        gui.update(90)
        self.assertEqual(gui.game.player.state, 8)
        with patch.object(gui, 'label', wraps=gui.label) as label:
            gui.draw()
        self.assertIn('POWER  0.7s', [call.args[0] for call in label.call_args_list])
        gui.game.player.state = 3
        self.assertIs(gui.ghost_sprite(), gui.sprites['ghost_white'])
        gui.restart()
        self.assertIs(gui.game.config, config)
        self.assertEqual(gui.game.player.state, 0)
        self.assertEqual(gui.game.env.cols, 8)


if __name__ == '__main__':
    unittest.main()
