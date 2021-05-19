#!/usr/bin/env python3

"""
IMPORTANT INFORMATION
_____________________

Before running this script, please make sure to have the following environment variables set:

DOWNWARD_ROOT           (path to the root directory of the Fast Downward planner, at the revision
                        with commit hash 09ccef5fd)

DOWNWARD_BENCHMARKS      (path to the benchmarks root directory from https://github.com/aibasel/downward-benchmarks)
"""

import copy
import logging
import os
import pprint
import re
import time

from minimizer.grid import slurm_tools
from lab import tools
from minimizer.aux import run_and_parse_all, run_all
from minimizer.evaluator import Evaluator
from minimizer.parser import Parser
from minimizer.run import Run
from minimizer.successor_generator import SuccessorGenerator


DOWNWARD_ROOT = os.environ["DOWNWARD_ROOT"]
DOWNWARD_BENCHMARKS = os.environ["DOWNWARD_BENCHMARKS"]


class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(1, 5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ


parser = Parser()


def facts_tracker(content, props):
    props["translator_facts"] = re.findall(r"Translator facts: (\d+)", content)


parser.add_function(facts_tracker, "succeeder")
parser.add_function(facts_tracker, "time-failer")
parser.add_function(facts_tracker, "memory-failer")


class MyEvaluator(Evaluator):
    def evaluate(self, state):
        logging.info(f"Evaluating:\n{pprint.pformat(state)}")
        eyedee = state["id"]
        if eyedee == 1:
            state["runs"]["succeeder"].start(state)
        elif eyedee == 2:
            state["runs"]["time-failer"].start(state)
        elif eyedee == 3:
            state["runs"]["memory-failer"].start(state)
        else:
            results = run_and_parse_all(state, parser)
            logging.info(f"Results:\n{pprint.pformat(results)}")

        return state["level"] <= 3 and state["id"] == 4


domain = os.path.join(DOWNWARD_BENCHMARKS, "tpp/domain.pddl")
problem1 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p05.pddl")
problem2 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p07.pddl")
# problem3 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p30.pddl")
search_arguments = ["--search", "astar(lmcut())"]
planner = [tools.get_python_executable(), os.path.join(DOWNWARD_ROOT, "fast-downward.py")]
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


my_environment = slurm_tools.MinimizerSlurmEnvironment(
    extra_options="#SBATCH --cpus-per-task=2",)

print(
    f"Search result:\n{pprint.pformat(slurm_tools.main(create_initial_state(), MyGenerator, MyEvaluator, my_environment, enforce_order=True))}")


# run_search()
# ./grid_test.py --> search_local
# ./grid_test.py --grid --> search_grid
# ./grid_test.py --evaluate directory_14 --> evaluate(load(directory_14/state))
