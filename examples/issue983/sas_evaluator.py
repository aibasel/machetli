import os
import re

from machetli import sas, tools

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(PLANNER_REPO, "builds/release/bin/downward")


def evaluate(state):
    with sas.temporary_file(state) as sas_filename:
        reference_command = [
            PLANNER, "--search", "astar(lmcut())", "--translate-options", "--relaxed",
        ]
        run_reference = tools.RunWithInputFile(
            reference_command, input_file=f"{sas_filename}", time_limit=20, memory_limit=3000)
        stdout, _, _ = run_reference.start()
        cost_re = re.compile("Plan cost: (\d+)$")
        match = cost_re.search(stdout)
        if match:
            cost = int(match.group())
        else:
            return False

        mip_command = [
            PLANNER, "--search",
            "astar(operatorcounting([delete_relaxation_constraints("
            "use_time_vars=true, use_integer_vars=true)], "
            "use_integer_operator_counts=True), bound=0)"
        ]
        run_mip = tools.RunWithInputFile(
            mip_command, input_file=f"{sas_filename}", time_limit=20, memory_limit=3000)
        stdout, _, _ = run_mip.start()
        initial_h_re = re.compile("Initial heuristic value * (\d+)$")
        match = initial_h_re.search(stdout)
        if match:
            initial_h = int(match.group())
        else:
            return False

        return cost < initial_h
