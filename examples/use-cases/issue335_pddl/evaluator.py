#!/usr/bin/env python3

import os
from pathlib import Path

from machetli import pddl, tools

PYTHON37 = os.environ["PYTHON_3_7"]
PLANNER_REPO = Path(os.environ["DOWNWARD_REPO"])
TRANSLATOR = PLANNER_REPO / "src/translate/translate.py"

# The evaluation function we are defining here is used in the search function.
# It is executed during the search to check if generated states still produce
# the behaviour we are searching for.
def evaluate(domain_filename, problem_filename):
    command = [PYTHON37, str(TRANSLATOR), f"{domain_filename}", f"{problem_filename}"]
    result = tools.run(command, cpu_time_limit=20, memory_limit=3338, text=True)

    return "AssertionError: Negated axiom impossible" in result.stderr

if __name__ == "__main__":
    pddl.run_evaluator(evaluate)
