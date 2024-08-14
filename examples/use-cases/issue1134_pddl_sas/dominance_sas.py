#!/usr/bin/env python3
import os
import platform
import pprint
import sys

from machetli import environments, sas, search, tools

if "DOWNWARD_REPO" not in os.environ:
    msg = """
Make sure to set the environment variable DOWNWARD_REPO.
    """
    sys.exit(msg)

script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)
problem_filename = os.path.join(script_dir, "problem.sas")

initial_state = sas.generate_initial_state(problem_filename)

evaluator_filename = os.path.join(os.path.dirname(tools.get_script_path()),
                                  "evaluator_sas.py")

environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(export=["DOWNWARD_REPO"])


result = search(initial_state, [sas.RemoveOperators(), sas.RemoveVariables(), sas.RemovePrePosts(), sas.SetUnspecifiedPreconditions(), sas.MergeOperators(), sas.RemoveGoals()],
                evaluator_filename, environment)

sas.write_file(result, "result.sas")

pprint.pprint(result)
