#!/usr/bin/env python3

import os

from machetli import sas, tools

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(PLANNER_REPO, "fast-downward.py")


def evaluate(sas_filename):
    solvable_command = [
        PLANNER, sas_filename, "--search",
        "astar(lmcount(lm_rhw(use_orders=false)))",
    ]
    solvable_stdout, _, _ = tools.run_with_limits(
        solvable_command, time_limit=10, memory_limit=3000)

    unsolvable_command = [
        PLANNER, sas_filename, "--search",
        "astar(lmcount(lm_rhw(use_orders=true)))",
    ]
    unsolvable_stdout, _, _ = tools.run_with_limits(
        unsolvable_command, time_limit=10, memory_limit=3000)

    return "Solution found." in solvable_stdout and \
            "Search stopped without finding a solution." in unsolvable_stdout

if __name__ == "__main__":
    sas.run_evaluator(evaluate)
