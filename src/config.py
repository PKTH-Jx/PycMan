"""Load shared defaults and map-specific JSON overrides."""
import json
from dataclasses import dataclass, fields
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / 'configs/arcade.json'
TERMINAL_CONFIG = PROJECT_ROOT / 'configs/naive.json'


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f'{path}: configuration must be a JSON object')
    return data


@dataclass(frozen=True)
class GameConfig:
    map_file: Path
    turn_ms: int
    get_point: int
    beat_ghost: int
    get_power: int
    power_turns: int
    flash_turns: int
    flash_interval: int

    def __post_init__(self) -> None:
        for name in ('turn_ms', 'power_turns', 'flash_interval',
                     'get_point', 'beat_ghost', 'get_power', 'flash_turns'):
            value = getattr(self, name)
            minimum = 1 if name in ('turn_ms', 'power_turns', 'flash_interval') else 0
            if type(value) is not int or value < minimum:
                raise ValueError(f'{name} must be an integer >= {minimum}')
        if self.flash_turns > self.power_turns:
            raise ValueError('flash_turns must not exceed power_turns')


def load_config(path: str | Path = DEFAULT_CONFIG) -> GameConfig:
    """Load a profile's shared game config, then apply its local overrides.

    map_file and game_config paths are relative to the profile file.
    Profiles without game_config use the project's defaults.json.
    """
    path = Path(path).resolve()
    profile = _read_json(path)
    game_config = profile.pop('game_config', None)
    if game_config is None:
        shared_path = PROJECT_ROOT / 'configs/defaults.json'
    elif isinstance(game_config, str) and game_config:
        shared_path = (path.parent / game_config).resolve()
    else:
        raise ValueError('game_config must be a nonempty path string')
    data = _read_json(shared_path)
    data.update(profile)
    unknown = data.keys() - {field.name for field in fields(GameConfig)}
    if unknown:
        raise ValueError(f'Unknown configuration keys: {", ".join(sorted(unknown))}')
    map_file = data.get('map_file')
    if not isinstance(map_file, str) or not map_file:
        raise ValueError('map_file must be a nonempty path string')
    data['map_file'] = (path.parent / map_file).resolve()
    return GameConfig(**data)


# Compatibility defaults; running games use their own GameConfig instance.
DEFAULT_SETTINGS = load_config()
TURN_MS = DEFAULT_SETTINGS.turn_ms
