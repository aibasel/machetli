#!/usr/bin/env python3
import os

from machetli.sas import generated_sas_file
from machetli.run import RunWithInputFile

REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(REPO, "builds/release/bin/downward")


def evaluate(state):
    # The context manager generated_sas_file temporarily writes our SAS+ task
    # to a file that is automatically deleted afterwards.
    with generated_sas_file(state) as sas_filename:
        command = [
            PLANNER, "--search",
            "astar(operatorcounting(constraint_generators=[state_equation_constraints()]))"]
        # The downward binary we are using takes stdin arguments, so we use the Run
        # implementation RunWithInputFile which enables us to pass the contents of
        # a file to stdin when *command* is executed.
        run = RunWithInputFile(command, 
                               input_file=f"{sas_filename}",
                               time_limit=10, memory_limit=3338)
        stdout, stderr, returncode = run.start(state)
    return "caught signal 11" in stdout or "caught signal 6" in stdout
