import json
import sys
from pathlib import Path


def load_config(path=None):
    if path and path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def write_file_with_confirmation(path: Path, content: str):
    if path.exists():
        if not ask_yes_no(f"The file '{path}' already exists. Overwrite?",
                False):
            return
    path.write_text(content)
    print(f"Wrote content to '{path}'")


def format_value(value, config):
    if isinstance(value, str):
        return value.format(**config)
    elif isinstance(value, list):
        return [format_value(entry, config) for entry in value]
    else:
        print("Value cannot be formatted")
        sys.exit("aborting")


def ask_yes_no(question, default=None):
    if default is True:
        prompt = f"{question} [Y/n]"
    elif default is False:
        prompt = f"{question} [y/N]"
    else:
        prompt = f"{question} [y/n]"
    while True:
        reply = input(prompt + "\n> ").strip().lower()
        if not reply and default is not None:
            return default
        elif reply in {"y", "yes"}:
            return True
        elif reply in {"n", "no"}:
            return False
        else:
            print("Please type 'y' or 'n'.")


def ask_selection(prompt, options):
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")
    while True:
        choice = input("> ")
        try:
            return options[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid input, please enter again.")


def ask_text(question, default=None):
    prompt = f"{question}"
    if default:
        prompt += f" [Default: {default}]"
    prompt += "\n> "
    return input(prompt) or default


def ask_value(config, key, prompt, default=None, options=None):
    existing = config.get(key)
    if existing:
        print(f"{key} already set: {existing}")
        return existing
    if options:
        value = ask_selection(prompt, options)
    else:
        value = ask_text(prompt, default)
    config[key] = value
    return value
