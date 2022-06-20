import os

from machetli import sas, tools

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(PLANNER_REPO, "fast-downward.py")


def evaluate(state):
    with sas.temporary_file(state) as sas_filename:
        reference_command = [
            PLANNER, sas_filename, "--search", "astar(lmcut())",
            "--translate-options", "--relaxed",
        ]
        reference_run = tools.Run(
            reference_command, time_limit=20, memory_limit=3000)
        stdout, stderr, _ = reference_run.start()
        cost = tools.parse(stdout, r"Plan cost: (\d+)")

        mip_command = [
            PLANNER, sas_filename, "--search",
            "astar(operatorcounting([delete_relaxation_constraints("
            "use_time_vars=true, use_integer_vars=true)], "
            "use_integer_operator_counts=True), bound=0)",
        ]
        mip_run = tools.Run(mip_command, time_limit=20, memory_limit=3000)
        stdout, stderr, _ = mip_run.start()
        initial_h = tools.parse(stdout, r"Initial heuristic value .* (\d+)")

        if cost is None or initial_h is None:
            return False
        return cost != initial_h
