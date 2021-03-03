
import copy
import subprocess
from downward_lib import pddl_parser, timers
import sys
import os
dirname = os.path.dirname(__file__)
downward_lib = os.path.join(dirname, "downward_lib/")
sys.path.append(downward_lib)
from pddl_writer import write_PDDL


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
    current_state = initial_state
    eve = evaluator()

    with timers.timing("Starting first-choice hill-climbing search"):
        for succ_gen in successor_generators:
            with timers.timing("Generating successors with class {}".format(succ_gen.__name__)):
                current_task = current_state["pddl_task"] if is_pddl_task else current_state["sas_task"]
                children = 0
                num_successors = 0
                print()
                while True:
                    if children > 0:
                        print("child found ({}), searched through {} successor(s)\n".format(children, num_successors)))
                    num_successors = 0
                    children += 1
                    for successor_task, removed_element in succ_gen.get_successors(current_task):
                        num_successors += 1
                        write_PDDL(successor_task, NEW_DOMAIN_FILENAME, NEW_PROBLEM_FILENAME)
                        current_state = update_state(current_state, successor_task)
                        if eve.evaluate(current_state):
                            


