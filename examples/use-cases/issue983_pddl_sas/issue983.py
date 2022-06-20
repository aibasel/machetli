#!/usr/bin/env python

import os
import platform
import subprocess
import sys

from machetli import environments, pddl, sas, search, tools

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")

if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(
        batch_size=100, export=["DOWNWARD_REPO"])
else:
    environment = environments.LocalEnvironment()

# This experiment was first conducted on Fast Downward revision 80c1b35 where
# h+ was inadmissible.

script_dir = os.path.dirname(tools.get_script_path())
domain = os.path.join(script_dir, "problem/p27-domain.pddl")
problem = os.path.join(script_dir, "problem/p27.pddl")

initial_state = pddl.generate_initial_state(domain, problem)
successor_generators = [
    pddl.RemovePredicates("true"),
    pddl.RemoveActions(),
    pddl.RemoveObjects(),
]
evaluator_filename = os.path.join(script_dir, "pddl_evaluator.py")
result = search(initial_state, successor_generators, evaluator_filename,
                environment)

pddl_result_names = (
    os.path.join(script_dir, "problem/small-domain.pddl"),
    os.path.join(script_dir, "problem/small-problem.pddl"),
)
pddl.write_files(result, pddl_result_names[0], pddl_result_names[1])

translate = [
    TRANSLATOR, pddl_result_names[0], pddl_result_names[1],
]
try:
    subprocess.check_call(translate)
except subprocess.CalledProcessError as err:
    cmd = " ".join(translate)
    sys.exit(f"Error: Call '{cmd}' failed.")

sas_file = os.path.join(script_dir, "output.sas")
initial_state = sas.generate_initial_state(sas_file)
successor_generators = [
    sas.RemoveOperators(),
    sas.RemoveVariables(),
    sas.RemovePrePosts(),
    sas.SetUnspecifiedPreconditions(),
    sas.MergeOperators(),
]
evaluator_filename = os.path.join(script_dir, "sas_evaluator.py")
result = search(initial_state, successor_generators, evaluator_filename,
                environment)
sas.write_file(result, "problem/result.sas")
