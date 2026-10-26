"""Minimal checks that the shared game can run and invoke task interfaces."""

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import io
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from config import load_config
from controller import KeyboardController, RandomController, WAIT
from game import Game, stage_setup
from gui import GUI
from rules import GameRules, stage_rules
from utils import Env, Ghost, Player, ROAD


def framework_stub() -> ModuleType:
    """Valid unfinished behavior independent of a student's files."""
    stub = ModuleType('framework_stub')
    stub.can_walk = lambda env, x, y: False
    stub.move = lambda agent, direction: False
    stub.advance_power = lambda player: None
    stub.collect_item = lambda player: None
    stub.resolve_collisions = lambda env: None
    stub.check_result = lambda game: 'running'
    stub.legal_directions = lambda controller: []
    stub.random_direction = lambda controller: WAIT
    stub.handle_key = lambda controller, key: False
    stub.continuous_direction = lambda controller: WAIT
    return stub


class FrameworkTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'map.txt'

    def map(self, text: str) -> Path:
        self.path.write_text(text, encoding='utf-8')
        return self.path

    def test_map_and_configuration_load(self):
        config = load_config('configs/training.json')
        env = Env(config.map_file, config)
        self.assertEqual((env.cols, env.rows), (11, 7))
        self.assertIsNotNone(env.player)
        self.assertGreaterEqual(len(env.ghosts), 1)
        self.assertEqual(env.get_tile(env.player.x, env.player.y), ROAD)
        with self.assertRaises(IndexError):
            env.get_tile(-1, 0)
        with self.assertRaises(IndexError):
            env.get_tile(env.cols, 0)

    def test_invalid_map_shape_and_player_count_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'same width'):
            Env(self.map('###\n#c\n###\n'))
        with self.assertRaisesRegex(ValueError, 'exactly one player'):
            Env(self.map('###\n#.#\n###\n'))

    def test_core_classes_invoke_injected_rule_interfaces(self):
        path = self.map('#######\n#c..g.#\n#######\n')
        called = []

        def record(name, value=None):
            called.append(name)
            return value

        rules = GameRules(
            can_walk=lambda env, x, y: record('can_walk', True),
            move=lambda agent, direction: record('move', True),
            advance_power=lambda player: record('advance_power'),
            collect_item=lambda player: record('collect_item'),
            resolve_collisions=lambda env: record('resolve_collisions'),
            check_result=lambda game: record('check_result', 'running'),
            legal_directions=lambda controller: record('legal_directions', []),
            random_direction=lambda controller: record('random_direction', WAIT),
            handle_key=lambda controller, key: record('handle_key', True),
            continuous_direction=lambda controller: record('continuous_direction', (1, 0)),
        )
        game = Game(path, rules=rules)
        ghost = game.env.ghosts[0]
        self.assertIs(type(game.env), Env)
        self.assertIs(type(game.player), Player)
        self.assertIs(type(ghost), Ghost)
        self.assertIs(type(game.controllers[game.player]), KeyboardController)
        self.assertIs(type(game.controllers[ghost]), RandomController)

        game.env.can_walk(2, 1)
        game.controllers[ghost].legal_directions()
        game.controllers[game.player].handle_key('right')
        game.step()
        self.assertEqual(set(called), set(GameRules.__dataclass_fields__))

    def test_turn_order_invalid_action_and_finished_game(self):
        path = self.map('#######\n#c..g.#\n#######\n')
        events = []

        def move(agent, direction):
            events.append('player_move' if isinstance(agent, Player) else 'ghost_move')
            return isinstance(agent, Player)

        rules = GameRules(
            move=move,
            advance_power=lambda player: events.append('tick'),
            collect_item=lambda player: events.append('collect'),
            resolve_collisions=lambda env: events.append('collision'),
            check_result=lambda game: events.append('result') or 'running',
            random_direction=lambda controller: events.append('ghost_decision') or WAIT,
        )
        game = Game(path, rules=rules)
        events.clear()  # Game checks the initial result during construction.
        with self.assertRaises(ValueError):
            game.step((2, 0))
        self.assertEqual(events, [])
        game.step((1, 0))
        self.assertEqual(events, [
            'tick', 'player_move', 'collect', 'collision', 'result',
            'ghost_decision', 'ghost_move', 'collision', 'result',
        ])
        game.status = 'won'
        events.clear()
        self.assertEqual(game.step((1, 0)), 'won')
        self.assertEqual(events, [])

    def test_stage_prefix_enables_expected_rules(self):
        stub = framework_stub()
        s1 = stage_rules('S1', stub)
        s5 = stage_rules('S5', stub)
        _, _, _, s1_keyboard, s1_ghost = stage_setup('S1', implementation=stub)
        _, _, _, s5_keyboard, s5_ghost = stage_setup('S5', implementation=stub)
        self.assertIsNotNone(s1.can_walk)
        self.assertIsNotNone(s1.move)
        self.assertIsNone(s1.advance_power)
        self.assertIsNone(s1.random_direction)
        self.assertIsNone(s1.handle_key)
        self.assertTrue(all(getattr(s5, name) is not None
                            for name in GameRules.__dataclass_fields__))
        self.assertTrue(issubclass(s1_keyboard, KeyboardController))
        self.assertIs(s5_keyboard, KeyboardController)
        self.assertIs(s5_ghost, RandomController)
        self.assertIsNot(s1_ghost, RandomController)

    def test_each_unfinished_stage_gui_draws_and_restarts(self):
        import pygame

        self.addCleanup(pygame.quit)
        for stage in ('S1', 'S2', 'S3', 'S4', 'S5'):
            with self.subTest(stage=stage):
                gui = GUI.for_stage(stage, implementation=framework_stub())
                self.assertEqual(gui.game.status, 'running')
                gui.draw()
                gui.player_controller.handle_key('right')
                gui.update(gui.config.turn_ms)
                gui.restart()
                self.assertEqual(gui.game.status, 'running')

    def test_stage_score_requires_every_test_to_pass(self):
        from tests.__main__ import STAGE_POINTS, complete

        self.assertEqual(sum(STAGE_POINTS.values()), 60)
        result = unittest.TestResult()
        result.testsRun = 3
        self.assertTrue(complete(result, 3))
        result.failures.append((None, 'failed case'))
        self.assertFalse(complete(result, 3))
        result.failures.clear()
        result.testsRun = 2
        self.assertFalse(complete(result, 3))

    def test_framework_failure_prevents_student_suite(self):
        from tests import __main__ as runner

        failed = unittest.TestResult()
        with (patch.object(runner, 'run_suite', return_value=failed),
              patch.object(runner, 'stage_suite', side_effect=AssertionError('student suite ran')),
              patch('sys.stdout', new_callable=io.StringIO) as output):
            self.assertEqual(runner.main(['S1']), 2)
        self.assertIn('Student tests were not run', output.getvalue())

    def test_stage_gets_no_points_when_cumulative_check_fails(self):
        from tests import __main__ as runner

        one_test = unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])
        framework = unittest.TestResult()
        framework.testsRun = unittest.defaultTestLoader.loadTestsFromTestCase(
            FrameworkTest).countTestCases()
        public = unittest.TestResult()
        public.testsRun = 1
        cumulative = unittest.TestResult()
        cumulative.testsRun = 1
        cumulative.failures.append((None, 'failed game check'))
        with (patch.object(runner, 'run_suite', side_effect=[framework, public, cumulative]),
              patch.object(runner, 'stage_suite', return_value=one_test),
              patch.object(runner, 'integration_suite', return_value=one_test),
              patch('sys.stdout', new_callable=io.StringIO) as output):
            self.assertEqual(runner.main(['S1']), 1)
        self.assertIn('S1: 0/14 points', output.getvalue())
        self.assertIn('cumulative check failed', output.getvalue())


if __name__ == '__main__':
    unittest.main()
