#!/usr/bin/env python3


import copy
import logging
import os.path
import platform
import pprint

from minimizer.grid import environments
from minimizer.main import main
from minimizer.tools import get_script_path
from minimizer.planning.generators import SuccessorGenerator

my_initial_state = {"level": 0, "id": 0}

class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ

my_evaluator_path = os.path.join(os.path.dirname(get_script_path()), "evaluator.py")

if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    my_environment = environments.BaselSlurmEnvironment(
        batch_size=2, allow_nondeterministic_successor_choice=True)
else:
    my_environment = environments.LocalEnvironment()

search_result = main(
    my_initial_state, MyGenerator, my_evaluator_path, my_environment)

logging.info(f"Search result:\n{pprint.pformat(search_result)}")
