#!/usr/bin/env python3

# In this example, we test how Machetli deals with calls running out of
# time or memory during the evaluation of a state. This is particularly
# interesting when running on the grid where tasks are not necessarily executed
# in order.

import copy
import logging
import os
import platform
import pprint
import sys

from machetli import environments
from machetli.successors import Successor, SuccessorGenerator
from machetli.search import search
from machetli.tools import get_script_path

if "DOWNWARD_REPO" not in os.environ:
    msg = """
Make sure to set the environment variable DOWNWARD_REPO to the path to a Fast
Downward repository (https://github.com/aibasel/downward) at a recent version
(mid-2021). Also make sure to build the executable.
"""
    sys.exit(msg)
if "DOWNWARD_BENCHMARKS" not in os.environ:
    msg = """
Make sure to set the environment variable DOWNWARD_BENCHMARKS to the path to a
planning benchmarks repository (https://github.com/aibasel/downward-benchmarks).
"""
    sys.exit(msg)


class MyGenerator(SuccessorGenerator):
    def get_successors(self, state):
        logging.info(f"Expanding:\n{pprint.pformat(state)}")
        for i in range(1, 5):
            succ = copy.deepcopy(state)
            succ["level"] = state["level"] + 1
            succ["id"] = i
            yield Successor(succ, "incresed level.")


environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(
        export=["DOWNWARD_REPO", "DOWNWARD_BENCHMARKS"],
        extra_options="#SBATCH --cpus-per-task=2",
        allow_nondeterministic_successor_choice=False)

evaluator_filename = os.path.join(os.path.dirname(get_script_path()),
                                  "evaluator.py")

search_result = search(
    {"level": 1, "id": 1},
    MyGenerator(),
    evaluator_filename,
    environment)

print(f"Search result:\n{pprint.pformat(search_result)}")
