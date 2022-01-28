#!/usr/bin/env python3

import os
import sys
import pprint

from minimizer.grid import environments
from minimizer import tools
from minimizer.planning import auxiliary
from minimizer.parser import Parser
from minimizer.evaluator import Evaluator
from minimizer.planning.generators import RemoveSASVariables, RemoveSASOperators
from minimizer.planning.sas_reader import write_SAS
from minimizer.run import RunWithInputFile, run_and_parse_all
from minimizer.main import main

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
    # We are  creating the entry "sas_task" because further down we are using the
    # state_with_generated_sas_file function from the auxiliary module and it expects
    # the SAS+ task to be stored behind that keyword.
    "sas_task": auxiliary.parse_sas_task(sas_filename),
    "runs": {
        # The downward binary we are using takes stdin arguments, so we use the Run
        # implementation RunWithInputFile which enables us to pass the contents of
        # a file to stdin when *command* is executed.
        "seg_fault": RunWithInputFile(command, input_file="{generated_sas_filename}",
                                      time_limit=10, memory_limit=3338)
    }
}

parser = Parser()


def assertion_error(content, props):
    props["error"] = "caught signal 11" in content or "caught signal 6" in content


parser.add_function(assertion_error, "seg_fault")


class MyEvaluator(Evaluator):
    def evaluate(self, state):
        # We want our SAS+ task to be available behind the generated_sas_filename
        # keyword, so we use the state_with_generated_sas_file context manager.
        with auxiliary.state_with_generated_sas_file(state) as local_state:
            results = run_and_parse_all(state, parser)
        return results["seg_fault"]["stdout"]["error"]


my_environment = environments.LocalEnvironment()

result = main(initial_state,
              [RemoveSASVariables, RemoveSASOperators],
              MyEvaluator,
              my_environment)

write_SAS(result["sas_task"], "result.sas")

pprint.pprint(result)
