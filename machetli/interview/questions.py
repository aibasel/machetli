import json
from pathlib import Path
from . import pddl, sas, pddl_then_sas


def get_general_questions():
    questions = [
        {
        "key_path": ["PLANNER"],
        "prompt": "Please specify the path to your planner:"
        }
    ]
    return questions


def load_config(path=None):
    if path and path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def get_from_config(config, key_path):
    d = config
    for key in key_path:
        if not isinstance(d, dict) or key not in d:
            return None
        d = d[key]
    return d


def set_in_config(config, key_path, value):
    d = config
    for key in key_path[:-1]:
        d = d.setdefault(key, {})
    d[key_path[-1]] = value


def substitute_placeholders(command_string, config, placeholders):
    def replace_token(token):
        for placeholder, path in placeholders.items():
            value = get_from_config(config, path)
            if value is not None:
                token = token.replace(f"{{{placeholder}}}", value)
        return token

    command_list = command_string.split()
    return [replace_token(token) for token in command_list]


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


def ask_value(config, key_path, prompt, default=None, options=None):
    existing = get_from_config(config, key_path)
    if existing:
        print(f"{' > '.join(key_path)} already set: {existing}")
        return existing
    if options:
        value = ask_selection(prompt, options)
    else:
        value = ask_text(prompt, default)
    set_in_config(config, key_path, value)
    return value


def select_module(config):
    value = ask_value(config, ["MODULE"],
              "Which kind of input do you want Machetli to simplify?",
              options=["PDDL domain and problem files", "A SAS^+ file",
                       "Start with PDDL files and then translate the result to "
                       "SAS^+ and continue simplifying"])
    if "pddl" in value.lower() and "sas" in value.lower():
        return pddl_then_sas
    elif "pddl" in value.lower():
        return pddl
    elif "sas" in value.lower():
        return sas
    else:
        return None


def start_interview(config_path=None):
    config = load_config(config_path)
    module = select_module(config)
    if module:
        for question in module.get_questions():
            ask_value(
                config,
                question["key_path"],
                question["prompt"],
                default=question.get("default"),
                options=question.get("options")
            )

    for question in get_general_questions():
        ask_value(
            config,
            question["key_path"],
            question["prompt"],
            default=question.get("default"),
            options=question.get("options")
        )

    output_path = (
        config_path
        if config_path is not None
        else Path("config_generated.json")
    )
    Path(output_path).write_text(json.dumps(config, indent=2))
    print(f"Wrote config to {output_path}")

    generate_run_py(config, module)


def generate_run_py(config, module, output_path=Path("run.py")):
    command_template = get_from_config(config, ["COMMAND_STRING"])
    if not command_template or not module:
        print("No COMMAND_STRING in config. Skipping run.py generation.")
        return

    placeholders = module.get_placeholders()
    cmd = substitute_placeholders(command_template, config, placeholders)
    code_template = (f"#!/usr/bin/env python3\n\n"
                     f"import subprocess\n\n"
                     f"subprocess.run({cmd})\n")

    output_path.write_text(code_template)
    print(
        f"Wrote file '{output_path}' from template. Execute it by "
        f"calling 'python3 {output_path}' from your command line."
    )
