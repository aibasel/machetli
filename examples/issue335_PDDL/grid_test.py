#!/usr/bin/env python

"""
IMPORTANT INFORMATION
_____________________

Before running this script, please make sure to have the following environment variables set:

DOWNWARD_ROOT   (path to the root directory of the Fast Downward planner, at the revision
                with commit hash 09ccef5fd)

PYTHON_3_7      (path to a Python 3.7 executable, as the Fast Downward version associated
                with this issue does not work with newer Python versions)
"""

import os
import pprint
import sys

from minimizer.grid import environments
from lab import tools
from minimizer.planning import auxiliary
from minimizer.parser import Parser
from minimizer.evaluator import Evaluator
from minimizer.search import first_choice_hill_climbing
from minimizer.planning.generators import RemoveObjects, ReplaceLiteralsWithTruth
from minimizer.planning.pddl_writer import write_PDDL
from minimizer.run import Run, run_and_parse_all, run_all
from minimizer.main import main

script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)


domain_filename = os.path.join(script_dir, "cntr-domain.pddl")
problem_filename = os.path.join(script_dir, "cntr-problem.pddl")

# os.environ.update({"PYTHON_3_7": "/infai/galluc00/.venv_minimizer/bin/python",
#                    "DOWNWARD_ROOT": "/infai/galluc00/downward"})

interpreter = os.environ["PYTHON_3_7"]
planner = os.path.join(
    os.environ["DOWNWARD_ROOT"], "src/translate/translate.py")
command = [interpreter, planner,
           "{generated_pddl_domain_filename}", "{generated_pddl_problem_filename}"]

initial_state = {
    "pddl_task": auxiliary.parse_pddl_task(domain_filename, problem_filename),
    "runs": {
        "issue335": Run(command, time_limit=20, memory_limit=3338)
    }
}

parser = Parser()


def assertion_error(content, props):
    props["assertion_error"] = "AssertionError: Negated axiom impossible" in content


parser.add_function(assertion_error, "issue335")


class MyEvaluator(Evaluator):
    def evaluate(self, state):
        with auxiliary.state_with_generated_pddl_files(state) as local_state:
            results = run_and_parse_all(local_state, parser)
        return results["issue335"]["stderr"]["assertion_error"]


my_environment = environments.BaselSlurmEnvironment(
    export=["PATH", "PYTHON_3_7", "DOWNWARD_ROOT"])

result = main(initial_state, [
                          RemoveObjects, ReplaceLiteralsWithTruth], MyEvaluator, my_environment)

write_PDDL(result["pddl_task"], "result-domain.pddl", "result-problem.pddl")

pprint.pprint(result["pddl_task"])

#run_search(initial_state, [RemoveObjects, ReplaceLiteralsWithTruth], MyEvaluator)
