#!/usr/bin/env python3

import os

from machetli import pddl, tools, evaluator

PYTHON37 = os.environ["PYTHON_3_7"]
PLANNER_REPO = os.environ["DOWNWARD_REPO"]
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")

# The evaluation function we are defining here is used in the search function.
# It is executed during the search to check if generated states still produce
# the behaviour we are searching for.
def evaluate(domain_filename, problem_filename):
    command = [PYTHON37, TRANSLATOR, f"{domain_filename}", f"{problem_filename}"]
    run = tools.Run(command, time_limit=20, memory_limit=3338)

    ## TODO: add functionality to store logs {always, only on error} to the Run class. See run.py run_all.
    stdout, stderr, returncode = run.start()

    ## TODO: add parsing methods?
    return "AssertionError: Negated axiom impossible" in stderr

if __name__ == "__main__":
    evaluator.main(evaluate, pddl)