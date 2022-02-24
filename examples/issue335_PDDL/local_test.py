#!/usr/bin/env python3

import os

from minimizer import tools
from minimizer.grid import environments
from minimizer.planning import auxiliary
from minimizer.planning.generators import RemoveObjects, ReplaceLiteralsWithTruth
from minimizer.planning.pddl_writer import write_PDDL
from minimizer.search import search

script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)

domain_filename = os.path.join(script_dir, "cntr-domain.pddl")
problem_filename = os.path.join(script_dir, "cntr-problem.pddl")

initial_state = {
    "pddl_task": auxiliary.parse_pddl_task(domain_filename, problem_filename),
}
successor_generators = [RemoveObjects(), ReplaceLiteralsWithTruth()]
evaluator_filename = os.path.join(script_dir, "evaluator.py")
environment = environments.LocalEnvironment()

result = search(initial_state, successor_generators, evaluator_filename, environment)

write_PDDL(result["pddl_task"], "result-domain.pddl", "result-problem.pddl")
