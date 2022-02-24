#!/usr/bin/env python3


import copy
import logging
import os.path
import platform
import pprint

from minimizer.grid import environments
from minimizer.search import search
from minimizer.tools import get_script_path
from minimizer.planning.generators import SuccessorGenerator

class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ

initial_state = {"level": 0, "id": 0}
successor_generator = MyGenerator()
evaluator_filename = os.path.join(os.path.dirname(get_script_path()), "evaluator.py")
environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(
        batch_size=2, allow_nondeterministic_successor_choice=True)

search_result = search(initial_state, successor_generator, evaluator_filename, environment)

logging.info(f"Search result:\n{pprint.pformat(search_result)}")
