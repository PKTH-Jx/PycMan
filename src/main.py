"""Run from any working directory: python path/to/src/main.py."""
from gui import GUI
from config import DEFAULT_CONFIG, load_config
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Pyc Man with a map profile')
    parser.add_argument('--config', default=DEFAULT_CONFIG, help='Path to a map JSON profile')
    args = parser.parse_args()
    GUI(config=load_config(args.config)).run()
