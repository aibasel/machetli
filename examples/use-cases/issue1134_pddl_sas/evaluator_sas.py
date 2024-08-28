#!/usr/bin/env python3

import os
import re

from machetli import sas, tools

REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(REPO, "builds/debug/bin/downward")
IF_CONFIG = "astar(operatorcounting([delete_relaxation_if_constraints(use_time_vars=true, use_integer_vars=false)], use_integer_operator_counts=false), bound=0)"
RR_CONFIG = "astar(operatorcounting([delete_relaxation_rr_constraints(acyclicity_type=time_labels, use_integer_vars=false)], use_integer_operator_counts=false), bound=0)"

def evaluate(sas_filename):
    h_if = get_h(IF_CONFIG, sas_filename)
    h_rr = get_h(RR_CONFIG, sas_filename)
    return h_if is not None and h_if > h_rr

def get_h(config, sas_filename):
    command = [PLANNER, "--search", config]
    result = tools.run_with_limits(
        command, time_limit=10, memory_limit=3338, input_file=sas_filename)
    for line in result.stdout.splitlines():
       if m := re.match(r".*Initial.*: (\d+)", line):
           return int(m.group(1))

if __name__ == "__main__":
    sas.run_evaluator(evaluate)
