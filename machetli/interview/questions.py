import json
from pathlib import Path
from machetli.interview import pddl, sas, pddl_then_sas, utils


def get_general_questions():
    questions = [
        {
            "key": "PLANNER",
            "prompt": "Please specify the path to your planner:"
        },
        {
            "key": "STRING_IN_OUTPUT",
            "prompt": "What string should I look for?"
        }
    ]
    return questions


def select_module(config):
    value = utils.ask_value(config, "MODULE",
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
    config = utils.load_config(config_path)
    module = select_module(config)
    if module:
        for question in module.get_questions():
            utils.ask_value(
                config,
                question["key"],
                question["prompt"],
                default=question.get("default"),
                options=question.get("options")
            )
        module.ask_command(config)

    for question in get_general_questions():
        utils.ask_value(
            config,
            question["key"],
            question["prompt"],
            default=question.get("default"),
            options=question.get("options")
        )

    output_path = (
        config_path
        if config_path is not None
        else "config.json"
    )
    utils.write_file_with_confirmation(Path(output_path),
                                       json.dumps(config, indent=2))

    generate_experiment(config, module)


def generate_experiment(config, module):
    command_template = config.get("COMMAND_AS_LIST")
    if not command_template or not module:
        print("No COMMAND_AS_LIST in config. "
              "Skipping experiment generation.")
        return

    formatted_config = {
        k: utils.format_value(v, config) for k, v in config.items()
    }
    experiment_template = module.get_experiment_template()
    evaluator_template = module.get_evaluator_template()
    experiment_template = experiment_template.format(**formatted_config)
    evaluator_template = evaluator_template.format(**formatted_config)

    experiment_output_path = Path("experiment.py")
    evaluator_output_path = Path("evaluator.py")
    utils.write_file_with_confirmation(experiment_output_path,
                                       experiment_template)
    utils.write_file_with_confirmation(evaluator_output_path,
                                       evaluator_template)
    print(
        f"Execute the experiment by calling "
        f"'python3 {experiment_output_path}' from your command line."
    )
