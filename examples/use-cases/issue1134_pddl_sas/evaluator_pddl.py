#!/usr/bin/env python3
import os
import re

from machetli import pddl, tools

REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(REPO, "fast-downward.py")


def get_h(config, dom_filename, prob_filename):
    command = [
        PLANNER, dom_filename, prob_filename, "--search",
        config
    ]
    run = tools.Run(command,
                    time_limit=10, memory_limit=3338)
    stdout, stderr, returncode = run.start()
    for line in stdout.splitlines():
       if m := re.match(r".*Initial.*: (\d+)", line):
           return int(m.group(1))

def evaluate(state):
    with pddl.temporary_files(state) as (dom_filename, prob_filename):
        h_if = get_h("astar(operatorcounting([delete_relaxation_if_constraints(use_time_vars=true, use_integer_vars=false)], use_integer_operator_counts=false), bound=0)",
                     dom_filename, prob_filename)
        h_rr = get_h("astar(operatorcounting([delete_relaxation_rr_constraints(acyclicity_type=time_labels, use_integer_vars=false)], use_integer_operator_counts=false), bound=0)",
                     dom_filename, prob_filename)
    return h_if is not None and h_if > h_rr
