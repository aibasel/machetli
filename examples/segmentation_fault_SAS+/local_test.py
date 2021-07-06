#!/usr/bin/env python
from lab import tools
import os
import sys

from minimizer.parser import Parser
from minimizer.evaluator import Evaluator
from minimizer.search import first_choice_hill_climbing
from minimizer.planning import auxiliary
from minimizer.planning.generators import RemoveSASVariables, RemoveSASOperators
from minimizer.planning.sas_reader import write_SAS
from minimizer.run import RunWithInputFile
from minimizer.run import run_and_parse_all

script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)
sas_filename = os.path.join(script_dir, "output_petri_sokobanp01.sas")

try:
    repo = os.environ["DOWNWARD_REPO"]
except KeyError:
    msg = """
Make sure to set the environment variable DOWNWARD_REPO.
It should point to the path of the Fast Downward repository
(https://github.com/aibasel/downward) at commit 3a27ea77f.
It is expected that the planner was built with an LP solver
(http://www.fast-downward.org/LPBuildInstructions).
    """
    sys.exit(msg)

planner = os.path.join(repo, "builds/release/bin/downward")
args = ["--search",
        "astar(operatorcounting(constraint_generators=[state_equation_constraints()]))"]
command = [planner] + args

initial_state = {
    "sas_task": auxiliary.parse_sas_task(sas_filename),
    "runs": {
        "seg_fault": RunWithInputFile(command, input_file="{generated_sas_filename}", time_limit=10, memory_limit=3338)
    }
}

parser = Parser()


def assertion_error(content, props):
    props["error_message"] = "caught signal 11" in content or "caught signal 6" in content


parser.add_function(assertion_error, "seg_fault")


class MyEvaluator(Evaluator):
    def evaluate(self, state):
        with auxiliary.state_with_generated_sas_file(state) as local_state:
            results = run_and_parse_all(state, parser)
        retcode = results["seg_fault"]["returncode"]
        return results["seg_fault"]["stdout"]["error_message"]


result = first_choice_hill_climbing(
    initial_state, [RemoveSASVariables, RemoveSASOperators], MyEvaluator)
write_SAS(result["sas_task"], "result.sas")
