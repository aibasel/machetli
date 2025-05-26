import argparse
from pathlib import Path
from machetli.interview import start_interview


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None,
                        help="Path to existing JSON config")
    args = parser.parse_args()

    start_interview(config_path=args.config)


if __name__ == "__main__":
    main()
