#!/usr/bin/env python3
import os
import platform
import pprint
import sys

from machetli import environments, pddl, search, tools

if "DOWNWARD_REPO" not in os.environ:
    msg = """
Make sure to set the environment variable DOWNWARD_REPO.
    """
    sys.exit(msg)

script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)
domain_filename = os.path.join(script_dir, "p11-domain.pddl")
problem_filename = os.path.join(script_dir, "p11-airport3-p1.pddl")

initial_state = pddl.generate_initial_state(domain_filename, problem_filename)

evaluator_filename = os.path.join(os.path.dirname(tools.get_script_path()),
                                  "evaluator_pddl.py")

environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(export=["DOWNWARD_REPO"])


result = search(initial_state, [pddl.RemoveActions(), pddl.RemovePredicates(), pddl.RemoveObjects()],
                evaluator_filename, environment)

pddl.write_files(result, "result_domain.pddl", "result.pddl")

pprint.pprint(result)
