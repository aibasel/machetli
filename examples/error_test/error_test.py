#!/usr/bin/env python3

# In this example, we test how the minimizer deals with calls running out of
# time or memory during the evaluation of a state. This is particularly
# interesting when running on the grid where tasks are not necessarily executed
# in order.

import copy
import logging
import os
import pprint

from minimizer.grid import environments
from minimizer.planning.generators import SuccessorGenerator
from minimizer.search import search

class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(1, 5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ

environment = environments.BaselSlurmEnvironment(
    extra_options="#SBATCH --cpus-per-task=2",)

evaluator_filename = os.path.join(os.path.dirname(get_script_path()), "evaluator.py")

search_result = search(
    {"level": 1, "id": 1},
    MyGenerator(),
    evaluator_filename,
    environment,
    allow_nondeterministic_successor_choice=False)

print(f"Search result:\n{pprint.pformat(search_result)}")
