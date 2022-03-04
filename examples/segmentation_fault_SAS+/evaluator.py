#!/usr/bin/env python3
import os
import sys

from minimizer.planning import auxiliary
from minimizer.run import RunWithInputFile

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

def evaluate(state):
    # We want our SAS+ task to be available behind the generated_sas_filename
    # keyword, so we use the state_with_generated_sas_file context manager.
    with auxiliary.state_with_generated_sas_file(state) as local_state:
        command = [
            os.path.join(repo, "builds/release/bin/downward"), "--search",
            "astar(operatorcounting(constraint_generators=[state_equation_constraints()]))"]
        # The downward binary we are using takes stdin arguments, so we use the Run
        # implementation RunWithInputFile which enables us to pass the contents of
        # a file to stdin when *command* is executed.
        run = RunWithInputFile(command, 
            input_file=f"{local_state['generated_sas_filename']}",
            time_limit=10, memory_limit=3338)
        stdout, stderr, returncode = run.start(state)
    return "caught signal 11" in stdout or "caught signal 6" in stdout
