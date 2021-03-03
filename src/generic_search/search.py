
import os
dirname = os.path.dirname(__file__)
downward_lib = os.path.join(dirname, "downward_lib/")
import sys
sys.path.append(downward_lib)
from downward_lib import pddl_parser, timers
import subprocess
import copy


NEW_DOMAIN_FILENAME = "minimized_domain.pddl"
NEW_PROBLEM_FILENAME = "minimized_problem.pddl"

def read_task(dom_filename, prob_filename):
    return pddl_parser.open(domain_filename=dom_filename, task_filename=prob_filename)

def run_tasks(state, parsers):
    if not isinstance(parsers, list):
        parsers = [parsers]
    results = {}
    props = Properties()
    for call in state["call_strings"]:
        output = subprocess.run(state["call_strings"][call], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
        with open("run.log", "w") as f:
            f.write(output)

        results[call] = {}
        for parser in parsers:
            parser.parse()
            results[call].update(copy.deepcopy(parser.props))

    for file in ["properties", "run.log", "sas_plan"]:
        os.remove(file)

    return results


def first_choice_hill_climbing(initial_state, successor_generators, evaluator):
    if not isinstance(successor_generators, list):
        successor_generators = [successor_generators]
    is_pddl_task = False
    if "pddl_task" in initial_state:
        is_pddl_task = True
    task = initial_state["pddl_task"] if is_pddl_task else initial_state["sas_task"]

    with timers.timing("Searching for smaller task using first-choice hill-climbing"):
        for succ_gen in successor_generators:
            pass


