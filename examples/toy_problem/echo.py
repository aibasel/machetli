#!/usr/bin/env python3


import copy
import logging
import platform
import pprint

from minimizer.grid import environments
from minimizer.evaluator import Evaluator
from minimizer.main import main
from minimizer.run import Run
from minimizer.planning.generators import SuccessorGenerator


class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(4):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield succ


"""
Expected search behavior:
Expanding: <0,0>
  Evaluating: <1,1>
  Evaluating: <2,1>
  Evaluating: <0,1>
  Evaluating: <3,1>
Expanding: <3,1>
  Evaluating: <1,2>
  Evaluating: <3,2>
Expanding: <3,2>
  Evaluating: <2,3>
  Evaluating: <1,3>
  Evaluating: <3,3>
  Evaluating: <0,3>
Search Result: <3,2>
"""
class MyEvaluator(Evaluator):
    def evaluate(self, state):
        state_id = state["id"]
        level = state["level"]
        logging.info(f"Evaluating: <id={state_id}, level={level}>")
        state["runs"]["echo"].start(state)

        return level <= 2 and state_id == 3


run = Run(["echo", "Hello", "world"])


def create_initial_state():
    return {"level": 0, "id": 0, "runs": {"echo": run}}


if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    my_environment = environments.BaselSlurmEnvironment(
        batch_size=2, enforce_order=False)
else:
    my_environment = environments.LocalEnvironment()

search_result = main(create_initial_state(),
                     MyGenerator,
                     MyEvaluator,
                     my_environment)

logging.info(f"Search result:\n{pprint.pformat(search_result)}")
