#!/usr/bin/env python3

import os
from pathlib import Path

from machetli import sas, tools

REPO = Path(os.environ["DOWNWARD_REPO"])
PLANNER = str(REPO / "builds/release/bin/downward")


def evaluate(sas_filename):
    command = [
        PLANNER, "--search",
        "astar(operatorcounting(constraint_generators=[state_equation_constraints()]))"]
    # The downward binary we are using takes stdin arguments, so we use the Run
    # implementation RunWithInputFile which enables us to pass the contents of
    # a file to stdin when *command* is executed.
    result = tools.run(command, input_filename=f"{sas_filename}",
                       cpu_time_limit=10, memory_limit=3338, text=True)
    return ("caught signal 11" in result.stdout or "caught signal 6" in result.stdout)

if __name__ == "__main__":
    sas.run_evaluator(evaluate)
