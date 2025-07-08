from importlib import resources

from machetli.templates import interview_templates
from machetli.interview.utils import ask_value


def get_questions():
    questions = [
        {
            "key": "DOMAIN",
            "prompt": "Please specify the domain file:"
        },
        {
            "key": "PROBLEM",
            "prompt": "Please specify the problem file:"
        }
    ]
    return questions


def ask_command(config):
    command = ask_value(config, "COMMAND_AS_LIST",
                    "How should the planner be executed? "
                    "Input the command line of your planner call, "
                    "using \"{planner}\" to represent the binary "
                    "and \"{domain}\"/\"{problem}\" to represent "
                    "the input files. For example {PLANNER} {DOMAIN} "
                    "{PROBLEM} --search astar(lmcut()).")
    if isinstance(command, str):
        config["COMMAND_AS_LIST"] = command.split()


def get_experiment_template():
    return resources.read_text(interview_templates, "experiment.py")


def get_evaluator_template():
    return resources.read_text(interview_templates, "evaluator.py")

