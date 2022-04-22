#!/usr/bin/env python

import errno
import os
import platform
import subprocess
import sys

from machetli import environments, pddl, sas, search, tools

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")

if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(
        batch_size=10, export=["DOWNWARD_REPO"])
else:
    environment = environments.LocalEnvironment()

# This experiment was first conducted on Fast Downward revision 80c1b35 where
# h+ was inadmissible.

script_dir = os.path.dirname(tools.get_script_path())
domain = "problem/p27-domain.pddl"
problem = "problem/p27.pddl"

initial_state = pddl.generate_initial_state(domain, problem)
successor_generators = [
    pddl.ReplaceLiteralsWithTruth(),
    pddl.RemoveActions(),
    pddl.RemoveObjects(),
]
evaluator_filename = os.path.join(script_dir, "pddl_evaluator.py")
result = search(initial_state, successor_generators, evaluator_filename,
                environment)

pddl_result_names = ("small-domain", "small-problem")
pddl.write_files(result, pddl_result_names[0], pddl_result_names[1])

translate = [
    TRANSLATOR, pddl_result_names[0], pddl_result_names[1],
]
try:
    process = subprocess.Popen(translate, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
except OSError as err:
    if err.errno == errno.ENOENT:
        cmd = " ".join(translate)
        sys.exit(f"Error: Call '{cmd}' failed.")
    else:
        raise

initial_state = sas.generate_initial_state("output.sas")
successor_generators = [
    sas.RemoveOperators(),
    sas.RemoveVariables(),
    sas.RemoveEffect(),
    sas.SetUnspecifiedPrevailCondition(),
    sas.MergeOperators(),
]
evaluator_filename = "sas_evaluator.py"
result = search(initial_state, successor_generators, evaluator_filename,
                environment)
sas.write_file(result, "problem/result")
