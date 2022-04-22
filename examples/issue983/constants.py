import os
import re

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(PLANNER_REPO, "builds/release/bin/downward")

REFERENCE_STRING = "astar(lmcut())"
MIP_STRING = \
    "astar(operatorcounting([delete_relaxation_constraints(use_time_vars=true, " \
    "use_integer_vars=true)], use_integer_operator_counts=True), bound=0)"

COST_RE = re.compile("Plan cost: (\d+)$")
INITIAL_H_RE = re.compile("Initial heuristic value * (\d+)$")


def get_reference_command(problem=None):
    if problem is None:
        problem = []
    return [PLANNER] + problem + ["--search", "astar(lmcut())",
                                  "--translate-options", "--relaxed"]


def get_mip_command(problem=None):
    if problem is None:
        problem = []
    return [PLANNER] + problem + [
        "--search",
        "astar(operatorcounting([delete_relaxation_constraints("
        "use_time_vars=true, use_integer_vars=true)], "
        "use_integer_operator_counts=True), bound=0)"
    ]
