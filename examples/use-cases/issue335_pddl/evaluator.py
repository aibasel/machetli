#!/usr/bin/env python3

import os

from machetli import pddl, tools

PYTHON37 = os.environ["PYTHON_3_7"]
PLANNER_REPO = os.environ["DOWNWARD_REPO"]
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")

# The evaluation function we are defining here is used in the search function.
# It is executed during the search to check if generated states still produce
# the behaviour we are searching for.
def evaluate(domain_filename, problem_filename):
    command = [PYTHON37, TRANSLATOR, f"{domain_filename}", f"{problem_filename}"]
    # TODO issue57: add functionality to store logs {always, only on error} to
    #  the run_with_limits function.
    result = tools.run_with_limits(command, time_limit=20, memory_limit=3338)

    ## TODO: add parsing methods?
    return "AssertionError: Negated axiom impossible" in result.stderr

if __name__ == "__main__":
    pddl.run_evaluator(evaluate)
