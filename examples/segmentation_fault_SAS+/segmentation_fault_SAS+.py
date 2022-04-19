#!/usr/bin/env python3
import os
import platform
import pprint
import sys

from machetli.grid import environments
from machetli.tools import get_script_path
from machetli import sas as sas
from machetli.search import search

if "DOWNWARD_REPO" not in os.environ:
    msg = """
Make sure to set the environment variable DOWNWARD_REPO.
It should point to the path of the Fast Downward repository
(https://github.com/aibasel/downward) at commit 3a27ea77f.
It is expected that the planner was built with an LP solver
(http://www.fast-downward.org/LPBuildInstructions).
    """
    sys.exit(msg)

script_path = get_script_path()
script_dir = os.path.dirname(script_path)
sas_filename = os.path.join(script_dir, "output_petri_sokobanp01.sas")

initial_state = {
    # We are  creating the entry "sas_task" because further down we use successor
    # generators that expect the SAS+ task to be stored behind that keyword.
    "sas_task": sas.parse_sas_task(sas_filename),
}

evaluator_filename = os.path.join(os.path.dirname(get_script_path()), "evaluator.py")

environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(export=["DOWNWARD_REPO"])


result = search(initial_state, [sas.RemoveSASVariables(),
                                sas.RemoveSASOperators()],
                evaluator_filename, environment)

sas.write_sas(result["sas_task"], "result.sas")

pprint.pprint(result)
