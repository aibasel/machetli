#!/usr/bin/env python3

# In this example, we showcase a simple custom successor generator and how to
# use custom values in the state. Our states here build a tree and each state is
# identified by its level in the tree and an ID enumerating the siblings. The
# evaluator in evaluator.py accepts a specific node on each level. It also shows
# how to run an external process as part of the evaluation.

import copy
import logging
import os.path
import platform
import pprint

from machetli import environments, search, tools
from machetli.successors import Successor, SuccessorGenerator


class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield Successor(succ, "increased level.")


initial_state = {"level": 0, "id": 0}
successor_generator = MyGenerator()
evaluator_filename = os.path.join(os.path.dirname(tools.get_script_path()),
                                  "evaluator.py")
environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(batch_size=2)

search_result = search(initial_state, successor_generator, evaluator_filename, environment)

logging.info(f"Search result:\n{pprint.pformat(search_result)}")
