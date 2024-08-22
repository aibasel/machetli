#!/usr/bin/env python3

import os
import time

from machetli import tools, evaluator

DOWNWARD_REPO = os.environ["DOWNWARD_REPO"]
DOWNWARD_BENCHMARKS = os.environ["DOWNWARD_BENCHMARKS"]
PYTHON = tools.get_python_executable()
PLANNER = os.path.join(DOWNWARD_REPO, "fast-downward.py")
PROBLEM1 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p05.pddl")
PROBLEM2 = os.path.join(DOWNWARD_BENCHMARKS, "tpp/p07.pddl")

def run_succeed():
    return tools.run_with_limits(
        [PYTHON, PLANNER, PROBLEM1, "--search", "astar(lmcut())"],
        time_limit=60, memory_limit=4000, log_output="on_fail")

def run_exceed_time_limit():
    return tools.run_with_limits(
        [PYTHON, PLANNER, PROBLEM2, "--search", "astar(lmcut())"],
        time_limit=10, memory_limit=4000, log_output="on_fail")

def run_exceed_memory_limit():
    return tools.run_with_limits(
        [PYTHON, PLANNER, "--search-memory-limit", "100M", PROBLEM2,
         "--search", "astar(lmcut())"], time_limit=1800, log_output="on_fail")


def evaluate(state):
    if state["id"] == 1:
        runs = [run_succeed]
    elif state["id"] == 2:
        runs = [run_exceed_time_limit]
    elif state["id"] == 3:
        runs = [run_exceed_memory_limit]
    elif state["id"] == 4:
        # simulate a slow failure that starts before a successful run
        time.sleep(70)
        assert False
    elif state["id"] == 5:
        runs = [run_succeed, run_exceed_time_limit, run_exceed_memory_limit]
    elif state["id"] == 6:
        # simulate a quick failure that starts after a successful run
        assert False
    else:
        time.sleep(50)
        runs = [run_succeed, run_exceed_time_limit, run_exceed_memory_limit]

    for run in runs:
        run()

    return state["level"] <= 3 and state["id"] == 5

if __name__ == "__main__":
    evaluator.run_evaluator(evaluate)
