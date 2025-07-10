import argparse
import json
from pathlib import Path
import shutil
import sys

from machetli.interview import planning
from machetli.interview.questions import run_interview, print_separator

def _load_config(path=None):
    if path and path.exists():
        with open(path, "rt") as f:
            return json.load(f)
    return {}

def _write_config(path, config):
    with open(path, "wt") as f:
        json.dump(config, f, indent=4)

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=Path, default=None,
                        help="Path to existing JSON config")
    parser.add_argument("-s", "--skip-interview", action="store_true", default=False,
                        help="Skip interview questions and use answers from config")
    args = parser.parse_args()
    if args.skip_interview and not args.config:
        print("Cannot skip the interview without providing a config file")
        sys.exit(1)
    return args

def _get_answers(config_path, skip_interview):
    config = _load_config(config_path)
    if skip_interview:
        return config
    else:
        # TODO: if we want to support questions from different modules, we need a
        # way to switch between them. This might need a more complex model of how to
        # go from one question to the next. For example, a function in each question
        # returning the key of the next question to ask.
        questions = planning.get_questions()
        return run_interview(questions, config)


def _generate_files(config):
    path = Path(config["script_location"])
    if path.exists():
        if config["overwrite_script_location"]:
            shutil.rmtree(path)
        else:
            print(f"Directory '{path}' exists. Skipping file generation.")
            exit(0)

    try:
        path.mkdir(parents=True, exist_ok=False)
    except:
        print(f"Could not create directory for scripts: '{path}'")
        sys.exit(1)

    config_path = path / "config.json"
    _write_config(config_path, config)

    main_script = planning.generate_files(config)

    print_separator()
    print(
        f"Machetli created the files for your search in the directory '{path}'. "
        "You can start the search by calling \n\n"
        f"    {main_script}\n\n"
        "from your command line."
        "To make changes to the setup, you can adapt those files or you can re-run "
        "this interview seeded with the answers given above with "
        f"'machetli -c {config_path}'"
    )

def main():
    args = _parse_args()
    answers = _get_answers(args.config, args.skip_interview)
    if answers:
        _generate_files(answers)

if __name__ == "__main__":
    main()
