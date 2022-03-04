#!/usr/bin/env python3
import os
import platform
import pprint

from minimizer.grid import environments
from minimizer.tools import get_script_path
from minimizer.planning import auxiliary
from minimizer.planning.generators import RemoveSASVariables, RemoveSASOperators
from minimizer.planning.sas_reader import write_SAS
from minimizer.search import search

script_path = get_script_path()
script_dir = os.path.dirname(script_path)
sas_filename = os.path.join(script_dir, "output_petri_sokobanp01.sas")


initial_state = {
    # We are  creating the entry "sas_task" because further down we use successor
    # generators that expect the SAS+ task to be stored behind that keyword.
    "sas_task": auxiliary.parse_sas_task(sas_filename),
}

evaluator_filename = os.path.join(os.path.dirname(get_script_path()), "evaluator.py")

environment = environments.LocalEnvironment()
if platform.node().endswith((".scicore.unibas.ch", ".cluster.bc2.ch")):
    environment = environments.BaselSlurmEnvironment(
        batch_size=2, allow_nondeterministic_successor_choice=True)


result = search(initial_state, [RemoveSASVariables(), RemoveSASOperators()],
                evaluator_filename, environment)

write_SAS(result["sas_task"], "result.sas")

pprint.pprint(result)
