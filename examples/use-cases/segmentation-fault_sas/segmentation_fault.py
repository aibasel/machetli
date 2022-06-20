#!/usr/bin/env python3
import os
import platform
import pprint
import sys

from machetli import environments, sas, search, tools

if "DOWNWARD_REPO" not in os.environ:
    msg = """
Make sure to set the environment variable DOWNWARD_REPO.
It should point to the path of the Fast Downward repository
(https://github.com/aibasel/downward) at commit 3a27ea77f.
It is expected that the planner was built with an LP solver
(http://www.fast-downward.org/LPBuildInstructions).
    """
    sys.exit(msg)

script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)
sas_filename = os.path.join(script_dir, "output_petri_sokobanp01.sas")

initial_state = sas.generate_initial_state(sas_filename)

evaluator_filename = os.path.join(os.path.dirname(tools.get_script_path()),
                                  "evaluator.py")

environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(export=["DOWNWARD_REPO"])


result = search(initial_state, [sas.RemoveVariables(), sas.RemoveOperators()],
                evaluator_filename, environment)

sas.write_file(result, "result.sas")

pprint.pprint(result)
