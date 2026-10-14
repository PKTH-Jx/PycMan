import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from controller import Controller, KeyboardController, RandomController, WAIT
from game import Game


class RightController(Controller):
    def get_direction(self):
        return (1, 0)


class WaitController(Controller):
    def get_direction(self):
        return WAIT


def make_game(text, **kwargs):
    with patch('builtins.open', return_value=io.StringIO(text)):
        return Game(**kwargs)


class ControllerTest(unittest.TestCase):
    def test_keyboard_buffer_and_no_mutation(self):
        game = make_game('#######\n#c....#\n###.###\n#######\n')
        controller = game.controllers[game.player]
        self.assertTrue(controller.handle_key('RIGHT'))
        before = [row[:] for row in game.env.env]
        self.assertEqual(controller.get_direction(), (1, 0))
        self.assertEqual(game.player.x, 1)
        self.assertEqual(game.env.env, before)
        game.step()
        controller.handle_key('down')
        game.step()  # Blocked turn stays buffered; continue right to junction.
        self.assertEqual((game.player.x, game.player.y), (3, 1))
        game.step()
        self.assertEqual((game.player.x, game.player.y), (3, 2))
        self.assertFalse(controller.handle_key('nonsense'))

    def test_random_legal_and_trapped(self):
        game = make_game('#######\n#c.g###\n####g##\n#######\n')
        walking, trapped = game.env.ghosts
        controller = game.controllers[walking]
        with patch('controller.random.choice', return_value=(-1, 0)) as choice:
            self.assertEqual(controller.get_direction(), (-1, 0))
            choice.assert_called_once_with([(-1, 0)])
        self.assertEqual((walking.x, walking.y), (3, 1))
        self.assertEqual(game.controllers[trapped].get_direction(), WAIT)
        self.assertIsNot(controller, game.controllers[trapped])
        self.assertIs(controller.agent, walking)

    def test_custom_player_and_ghost_strategies(self):
        game = make_game('########\n#c..g..#\n########\n',
                         player_controller=RightController, ghost_controller=RightController)
        game.step()
        self.assertEqual(game.player.x, 2)
        self.assertEqual(game.player.score, 10)
        self.assertEqual(game.env.ghosts[0].x, 5)
        ghost = game.env.ghosts[0]
        game.controllers[ghost] = WaitController(ghost)
        game.step()
        self.assertEqual(ghost.x, 5)

    def test_dead_ghost_controller_not_called(self):
        game = make_game('######\n#c.g.#\n######\n')
        ghost = game.env.ghosts[0]
        ghost.live = False
        with patch.object(game.controllers[ghost], 'get_direction') as direction:
            game.step(WAIT)
            direction.assert_not_called()

    def test_invalid_strategy_result(self):
        game = make_game('#####\n#c..#\n#####\n')
        game.player.state = 3
        with patch.object(game.controllers[game.player], 'get_direction', return_value=(2, 0)):
            with self.assertRaisesRegex(ValueError, 'KeyboardController returned invalid direction'):
                game.step()
        self.assertEqual(game.player.state, 3)
        self.assertEqual(game.player.x, 1)

    def test_terminal_keyboard_one_shot(self):
        game = make_game('#####\n#c..#\n#####\n')
        controller = KeyboardController(game.player, continuous=False)
        controller.handle_key('d')
        self.assertEqual(controller.get_direction(), (1, 0))
        self.assertEqual(controller.get_direction(), WAIT)
        controller.handle_key('')
        self.assertEqual(controller.get_direction(), WAIT)
        with patch('builtins.input', side_effect=['d', '', 'q']), patch('builtins.print'):
            game.run()
        self.assertEqual(game.player.x, 2)
        self.assertEqual(game.status, 'quit')


if __name__ == '__main__':
    unittest.main()
