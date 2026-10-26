"""Run from any working directory: python path/to/src/main.py."""
from gui import GUI
from config import load_config
from rules import STAGES
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a cumulative Pyc Man task stage')
    parser.add_argument('--config', help='Path to a map JSON profile')
    parser.add_argument('--map', help='Optional text map')
    parser.add_argument('--stage', choices=STAGES, help='Run the selected S1-S5 stage')
    args = parser.parse_args()
    config = load_config(args.config) if args.config else None
    GUI.for_stage(args.stage or 'S1', path=args.map, config=config).run()
