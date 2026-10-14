# PycMan 游戏与开发说明

本文记录当前可运行游戏的规则、配置与扩展接口。课程任务设计见 [任务设计草案](assignment-design.md)，项目入口见 [README](../Readme.md)。

## Run

Requires Python 3.10+ and pygame-ce (imported as `pygame`). From this folder:

```bash
python -m pip install -r requirements.txt
python src/main.py
```

Arrow keys / WASD start and steer. Movement continues automatically; turns are
buffered until a passage opens. Space / P pauses, R or the RESTART button starts
a fresh game immediately (initially moving right), Escape exits.
Losing window focus pauses the game. Collect every dot to win; touching a ghost
loses unless powered. Small dots give 10 points. Large golden dots (`o` in a
map) give 50 points and power for 40 simulation updates (7.2 seconds at the
180 ms update interval). Pyc Man keeps his normal size. Frightened ghosts turn blue and can be eaten for
50 points each. During the last 12 updates (2.16 seconds), ghosts alternate blue
and white every two updates to warn that power is ending. White ghosts are still
edible; at zero, they regain their original color and become dangerous again. Eaten ghosts stay
removed until restart. Another power dot refreshes the timer, without stacking.
The header shows remaining simulation time and a duration bar. Pausing or ending
the game freezes the timer; waiting or hitting a wall still consumes time.
At the start of each valid update, the previous duration decreases by one;
pickup then refreshes it before collision checks. Both dot types must be eaten
to win. The existing rules reset score on death.

Duration is configured by `power_turns` and update timing by `turn_ms` in the
JSON configurations described below. Close and relaunch a running
window after editing source code so it loads the new version.

`src/gui.py` handles events, a 180 ms logic timer, and 60 FPS drawing.
`src/controller.py` chooses movement directions (keyboard or random).
`src/game.py` remains independent of pygame and provides `Game.step()`.
`src/utils.py` owns terrain, characters, and collision rules.
`src/codebook.py` defines tile identifiers and the text-map character mapping
(`CODEBOOK`), which `utils.py` imports. Edit that file to change map symbols.
The GUI uses `assets/maps/arcade_map.txt`; the original terminal demonstration
still uses `naive_map.txt` and can be run with `python src/game.py`.

Player and ghost PNGs in `assets/sprites` were generated with the built-in
imagegen tool, with transparency preserved. Walls and dots are drawn by pygame.
Generation prompts are recorded in `assets/sprites/prompts.json`.

## Map configurations

`configs/defaults.json` stores shared timing, scores, power duration, and ghost
flash settings. Each map profile selects a `map_file` and references a shared
settings file with `game_config`. `configs/arcade.json` and `configs/naive.json`
both reference `defaults.json` and can override any shared setting.
The GUI defaults to the arcade profile; the
terminal demo defaults to the naive profile. Both retain their previous rules.

For example, create `configs/fast.json`:

```json
{
  "map_file": "../assets/maps/arcade_map.txt",
  "game_config": "defaults.json",
  "turn_ms": 120,
  "power_turns": 60,
  "get_point": 20
}
```

Launch it with `python src/main.py --config configs/fast.json`, or use
`python src/game.py --config configs/fast.json` for the terminal. Both `map_file`
and `game_config` paths are relative to the profile file. The loader reads the
referenced game configuration first, then applies settings from the map profile.
Several maps can reference the same settings file, or reference different files
for different rule sets. Profiles without `game_config` use the project's
`configs/defaults.json` for compatibility.
Scores and `flash_turns` must be nonnegative integers; `turn_ms`, `power_turns`,
and `flash_interval` must be positive integers. `flash_turns` cannot exceed
`power_turns` (override it too when choosing a duration below 12 turns).

For experiments in Python:

```python
from config import load_config
from game import Game

game = Game(config=load_config('configs/fast.json'))
print(game.config.turn_ms)
```

`GUI(config=load_config(...))` accepts the same configuration and preserves it
on restart. Each game owns its settings, so games can use different profiles
in the same process. Existing `Game(path)` and `GUI(path)` calls still work;
an explicit map path overrides the profile's map while keeping its parameters.
The codebook remains in `src/codebook.py`, shared by all text maps.

### Playable maps

Select any profile with `python src/main.py --config configs/<name>.json`.
The same profiles work with the terminal demo.

| Profile | Size | Ghosts | Turn time | Power duration | Layout |
| --- | --- | --- | --- | --- | --- |
| `training` | 11 × 7 | 1 | 240 ms | 50 turns | Small maze with loops and two power dots |
| `crossroads` | 15 × 11 | 2 | 180 ms | 40 turns | Central crossing with branching passages |
| `labyrinth` | 19 × 13 | 3 | 150 ms | 30 turns | Winding passages, shortcuts, and dead ends |
| `arcade` | 19 × 15 | 2 | 180 ms | 40 turns | Original arcade layout |
| `naive` | 10 × 3 | 1 | 180 ms | 40 turns | Original terminal corridor |

New profiles reference `defaults.json` and override timing and power duration
where shown. All playable maps have connected passages and reachable items.
The labyrinth player starts facing a wall; move down to leave the starting area.

`tests/maps/` contains small reusable fixtures for corridor wins, powered and
unpowered collisions, buffered turns at a junction, and open map boundaries.
Files prefixed `invalid_` intentionally exercise map validation.
`tests/test_maps.py` checks these scenarios, clears each playable map with ghosts
disabled to verify collectible reachability, and checks GUI rendering/restart
for the new maps using SDL's dummy driver.

## Checks

```bash
python -m unittest discover -s tests -v
```

The GUI tests use SDL's dummy video driver; they do not open a visible window.
Image loading follows the [pygame-ce image documentation](https://pyga.me/docs/ref/image.html).

## Frightened appearance references

- [Official PAC-MAN character page](https://pacman.com/en/character/): power pellets turn ghosts blue.
- [Licensed game instructions](https://m.media-amazon.com/images/I/B1wEAy0DgMS.pdf): flashing white warns that ghosts will soon become harmful again.
- [Nintendo-hosted PAC-MAN manual](https://www.nintendo.co.jp/clv/manuals/en/pdf/CLV-P-NABME_en.pdf): eaten ghosts return to the center and regenerate in the original game.

This teaching version reproduces the blue/white warning, but keeps its simpler
rules: random ghost movement, fixed duration, fixed ghost score, and no ghost
respawn until restart. The warning timing is our own setting, not an exact
reproduction of original arcade timing. Blue and white frightened variants were
made with built-in imagegen; their edit prompts are stored with the sprites.

## Writing a new controller

Each agent has its own `Controller` object. Implement `get_direction()` and
return `(dx, dy)`: right `(1, 0)`, down `(0, 1)`, left `(-1, 0)`, up `(0, -1)`,
or wait `(0, 0)`. Read `self.agent`, `self.agent.env`, and `legal_directions()`
to decide; do not call `move()` or change game state in the controller.
`Game` executes actions and handles points, power, collisions and results.

```python
from controller import Controller
from gui import GUI

class StudentController(Controller):
    def get_direction(self):
        choices = self.legal_directions()
        # Replace with your own search or decision strategy.
        return choices[0] if choices else (0, 0)

# Put in src/main.py. Keep the player on keyboard; replace ghost strategy.
if __name__ == '__main__':
    GUI(ghost_controller=StudentController).run()
```

Use `GUI(player_controller=StudentController)` to automate the player instead;
it starts automatically. `Game` accepts the same constructor options for
experiments without a window. Pass a controller class (or a factory accepting
one agent), not a pre-created instance. Each restart constructs fresh agents
and controllers. For different strategies per ghost, assign
`game.controllers[ghost] = StudentController(ghost)` after creating the game.

`KeyboardController` receives key names via `handle_key('right')` and handles
continuous movement and buffered turns. It does not import pygame. The GUI only
translates keyboard events to key names and manages pause/restart/exit.
The terminal demo uses `KeyboardController(continuous=False)` for one action
per entered command. `RandomController` chooses only legal moves, waiting when
trapped. Other controllers inherit a no-op `handle_key()`.

Call `game.step()` to use controllers. `game.step((dx, dy))` remains available
as a one-turn override for the player in tests; ghost controllers still run.
Controllers are queried sequentially: the player first, then each living ghost
using the current world state. A finished game does not query controllers.
