#!/usr/bin/env python3

import os
import re

from machetli import pddl, tools

REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(REPO, "fast-downward.py")
IF_CONFIG = "astar(operatorcounting([delete_relaxation_if_constraints(use_time_vars=true, use_integer_vars=false)], use_integer_operator_counts=false), bound=0)"
RR_CONFIG = "astar(operatorcounting([delete_relaxation_rr_constraints(acyclicity_type=time_labels, use_integer_vars=false)], use_integer_operator_counts=false), bound=0)"

def evaluate(domain_filename, problem_filename):
    h_if = get_h(IF_CONFIG, domain_filename, problem_filename)
    h_rr = get_h(RR_CONFIG, domain_filename, problem_filename)
    return h_if is not None and h_if > h_rr

def get_h(config, domain_filename, problem_filename):
    command = [PLANNER, domain_filename, problem_filename, "--search", config]
    result = tools.run(command, timeout=10, memory_limit=3338)
    for line in result.stdout.splitlines():
       if m := re.match(r".*Initial.*: (\d+)", line):
           return int(m.group(1))

if __name__ == "__main__":
    pddl.run_evaluator(evaluate)
