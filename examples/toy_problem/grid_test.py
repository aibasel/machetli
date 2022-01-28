#!/usr/bin/env python3


import copy
import logging
import os
import sys
import pprint
import re

from minimizer.grid import environments
from minimizer import tools
from minimizer.evaluator import Evaluator
from minimizer.main import main
from minimizer.parser import Parser
from minimizer.run import Run, run_and_parse_all
from minimizer.planning.generators import SuccessorGenerator

try:
    DOWNWARD_REPO = os.environ["DOWNWARD_REPO"]
    DOWNWARD_BENCHMARKS = os.environ["DOWNWARD_BENCHMARKS"]
except KeyError:
    msg = """
Make sure to set the environment variables DOWNWARD_REPO and DOWNWARD_BENCHMARKS.
DOWNWARD_REPO:          Path to Fast Downward repository (https://github.com/aibasel/downward)
                        at a recent version (mid-2021). Also make sure to build the executable.
DOWNWARD_BENCHMARKS:    Path to planning benchmarks repository
                        (https://github.com/aibasel/downward-benchmarks).
"""
    sys.exit(msg)


class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(1, 5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ


parser = Parser()

# The parsing result should be the same, regardless whether the function facts_tracker
# is used or the pattern directly.


def facts_tracker(content, props):
    props["translator_facts"] = re.findall(r"Translator facts: (\d+)", content)


parser.add_function(facts_tracker, ["succeeder", "time-failer"])

parser.add_pattern("translator_facts",
                   r"Translator facts: (\d+)", "memory-failer")


class MyEvaluator(Evaluator):
    def evaluate(self, state):
        logging.info(f"Evaluating:\n{pprint.pformat(state)}")
        if state["id"] == 1:
            state["runs"]["succeeder"].start(state)
        elif state["id"] == 2:
            state["runs"]["time-failer"].start(state)
        elif state["id"] == 3:
            state["runs"]["memory-failer"].start(state)
        else:
            results = run_and_parse_all(state, parser)
            logging.info(f"Results:\n{pprint.pformat(results)}")

        return state["level"] <= 3 and state["id"] == 4


domain = os.path.join(DOWNWARD_BENCHMARKS, "tpp/domain.pddl")
problem1 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p05.pddl")
problem2 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p07.pddl")
search_arguments = ["--search", "astar(lmcut())"]
planner = [tools.get_python_executable(), os.path.join(
    DOWNWARD_REPO, "fast-downward.py")]
planner_and_domain = planner + [domain]

# run1 succeeds, run2 fails on time limit, run3 fails on memory limit
run1 = Run(planner_and_domain + [problem1] + search_arguments,
           time_limit=60, memory_limit=4000, log_output="on_fail")

run2 = Run(planner_and_domain + [problem2] + search_arguments,
           time_limit=10, memory_limit=4000, log_output="on_fail")

run3 = Run(planner + ["--search-memory-limit", "100M"] + [problem2] + search_arguments,
           time_limit=1800, log_output="on_fail")


def create_initial_state():
    return {
        "level": 1, "id": 1, "runs": {
            "succeeder": run1,
            "time-failer": run2,
            "memory-failer": run3
        }
    }


my_environment = environments.BaselSlurmEnvironment(
    extra_options="#SBATCH --cpus-per-task=2",)

search_result = main(create_initial_state(),
                     MyGenerator,
                     MyEvaluator,
                     my_environment,
                     enforce_order=False)

print(f"Search result:\n{pprint.pformat(search_result)}")
