#!/usr/bin/env python3

# In this example, we test how the minimizer deals with calls running out of
# time or memory during the evaluation of a state. This is particularly
# interesting when running on the grid where tasks are not necessarily executed
# in order.

import copy
import logging
import os
import platform
import pprint

from minimizer.grid import environments
from minimizer.planning.generators import SuccessorGenerator
from minimizer.search import search
from minimizer.tools import get_script_path

class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(1, 5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ

environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(
        extra_options="#SBATCH --cpus-per-task=2",
        allow_nondeterministic_successor_choice=False)

evaluator_filename = os.path.join(os.path.dirname(get_script_path()), "evaluator.py")

search_result = search(
    {"level": 1, "id": 1},
    MyGenerator(),
    evaluator_filename,
    environment)

print(f"Search result:\n{pprint.pformat(search_result)}")
