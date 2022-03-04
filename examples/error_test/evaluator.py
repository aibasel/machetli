#!/usr/bin/env python3

import os
import sys

from minimizer import tools
from minimizer.run import Run

try:
    DOWNWARD_REPO = os.environ["DOWNWARD_REPO"]
    DOWNWARD_BENCHMARKS = os.environ["DOWNWARD_BENCHMARKS"]
except KeyError:
    msg = """
Make sure to set the environment variables DOWNWARD_REPO and DOWNWARD_BENCHMARKS.
DOWNWARD_REPO:          Path to Fast Downward repository (https://github.com/aibasel/downward)
                        at a recent version (mid-2021). Also make sure to build the executable.
DOWNWARD_BENCHMARKS:    Path to planning benchmarks repository
                        (https://github.com/aibasel/downward-benchmarks).
"""
    sys.exit(msg)

python = tools.get_python_executable()
planner = os.path.join(DOWNWARD_REPO, "fast-downward.py")
problem1 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p05.pddl")
problem2 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p07.pddl")

run_succeed = Run(
    [python, planner, problem1, "--search", "astar(lmcut())"],
    time_limit=60, memory_limit=4000, log_output="on_fail")

run_fail_time_limit = Run(
    [python, planner, problem2, "--search", "astar(lmcut())"],
    time_limit=10, memory_limit=4000, log_output="on_fail")

run_fail_memory_limit = Run(
    [python, planner, "--search-memory-limit", "100M", problem2,
        "--search", "astar(lmcut())"],
    time_limit=1800, log_output="on_fail")


def evaluate(state):
    runs = []
    if state["id"] == 1:
        runs = [run_succeed]
    elif state["id"] == 2:
        runs = [run_fail_time_limit]
    elif state["id"] == 3:
        runs = [run_fail_memory_limit]
    else:
        runs = [run_succeed, run_fail_time_limit, run_fail_memory_limit]

    for run in runs:
        run.start(state)

    return state["level"] <= 3 and state["id"] == 4


