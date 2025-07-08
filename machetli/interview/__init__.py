import argparse
import json
from pathlib import Path

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
    parser.add_argument("-q", "--quiet", action="store_true", default=False,
                        help="Skip interview questions and use answers from config")
    return parser.parse_args()

def _get_answers(config_path, quiet):
    config = _load_config(config_path)
    # TODO: if we want to support questions from different modules, we need a
    # way to switch between them. This might need a more complex model of how to
    # go from one question to the next. For example, a function in each question
    # returning the key of the next question to ask.
    questions = planning.get_questions()
    if quiet:
        return config
    else:
        return run_interview(questions, config)


def _generate_files(config):
    path = Path(config["script_location"])
    try:
        path.mkdir(parents=True, exist_ok=False)
    except:
        print(f"Could not create directory for scripts: '{path}'")

    config_path = path / "config.json"
    _write_config(config_path, config)

    main_script = planning.generate_files(config)

    print_separator()
    print(
        f"Machetli created the files for your search in the directory '{path}'. "
        "To make changes to the setup, you can adapt those files or you can re-run "
        "this interview with the answers given above with\n"
        f"    machetli -c {config_path}\n"
        "You can start the search by calling \n\n"
        f"    {main_script}\n\n"
        "from your command line."
    )

def main():
    args = _parse_args()
    answers = _get_answers(args.config, args.quiet)
    if answers:
        _generate_files(answers)

if __name__ == "__main__":
    main()
