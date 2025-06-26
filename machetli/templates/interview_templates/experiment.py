#!/usr/bin/env python

import platform

from machetli import environments, pddl, search, tools

if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(batch_size=100)
else:
    environment = environments.LocalEnvironment()

script_dir = tools.get_script_dir()
domain = script_dir / "domain.pddl"
problem = script_dir / "problem.pddl"

initial_state = pddl.generate_initial_state(domain, problem)
successor_generators = [
    pddl.RemovePredicates(replace_with="true"),
    pddl.RemoveActions(),
    pddl.RemoveObjects(),
]
evaluator_filename = script_dir / "evaluator.py"
result = search(initial_state, successor_generators, evaluator_filename,
                environment)

pddl.write_files(result,
                 script_dir / "small-domain.pddl",
                 script_dir / "small-problem.pddl")

