import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from game import Game
from utils import POWER, ROAD, POWER_TURNS, GET_POWER, BEAT_GHOST


def game_with_map(text):
    with patch('builtins.open', return_value=io.StringIO(text)):
        return Game()


class PowerTest(unittest.TestCase):
    def test_pickup_refresh_and_expiry(self):
        game = game_with_map('########\n#co o .#\n########\n')
        game.step((1, 0))
        self.assertEqual(game.player.state, POWER_TURNS)
        self.assertEqual(game.player.score, GET_POWER)
        self.assertEqual(game.env.get_tile(2, 1), ROAD)
        game.step((0, 0))
        self.assertEqual(game.player.state, POWER_TURNS - 1)
        game.step((1, 0))
        game.step((1, 0))
        self.assertEqual(game.player.state, POWER_TURNS)
        for _ in range(POWER_TURNS - 1):
            game.step((0, 0))
        self.assertEqual(game.player.state, 1)
        game.step((0, 0))
        self.assertEqual(game.player.state, 0)
        game.step((0, 0))
        self.assertEqual(game.player.state, 0)

    def test_power_protects_on_pickup(self):
        game = game_with_map('######\n#co.g#\n######\n')
        game.env.ghosts[0].x = 2
        game.step((1, 0))
        self.assertTrue(game.player.live)
        self.assertFalse(game.env.ghosts[0].live)
        self.assertEqual(game.player.score, GET_POWER + BEAT_GHOST)

    def test_expired_before_collision(self):
        game = game_with_map('#####\n#cg.#\n#####\n')
        game.player.state = 1
        self.assertEqual(game.step((1, 0)), 'lost')
        self.assertEqual(game.player.state, 0)

    def test_walls_consume_time_invalid_input_does_not(self):
        game = game_with_map('#####\n#c.o#\n#####\n')
        game.player.state = 3
        game.step((-1, 0))
        self.assertEqual(game.player.state, 2)
        with self.assertRaises(ValueError):
            game.step((2, 0))
        self.assertEqual(game.player.state, 2)

    def test_power_required_for_win_and_finished_timer_freezes(self):
        game = game_with_map('####\n#co#\n####\n')
        self.assertEqual(game.status, 'running')
        self.assertEqual(game.step((1, 0)), 'won')
        game.step((0, 0))
        self.assertEqual(game.player.state, POWER_TURNS)

    def test_ghost_preserves_power(self):
        game = game_with_map('######\n#c.og#\n######\n')
        ghost = game.env.ghosts[0]
        ghost.move((-1, 0))
        ghost.move((1, 0))
        self.assertEqual(game.env.get_tile(3, 1), POWER)


if __name__ == '__main__':
    unittest.main()
