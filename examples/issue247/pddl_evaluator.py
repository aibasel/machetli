import os

from machetli import pddl, tools

PLANNER_REPO = os.environ["DOWNWARD_REPO"]
PLANNER = os.path.join(PLANNER_REPO, "fast-downward.py")


def evaluate(state):
    with pddl.temporary_files(state) as (domain, problem):
        solvable_command = [
            PLANNER, domain, problem, "--search",
            "astar(lmcount(lm_rhw(use_orders=false)))",
        ]
        solvable = tools.Run(
            solvable_command, time_limit=10, memory_limit=3000)
        stdout, stderr, _ = solvable.start()
        solvable_out, solvable_err, _ = solvable.start()

        unsolvable_command = [
            PLANNER, domain, problem, "--search",
            "astar(lmcount(lm_rhw(use_orders=true)))",
        ]
        unsolvable = tools.Run(
            unsolvable_command, time_limit=10, memory_limit=3000)
        unsolvable_out, unsolvable_err, _ = unsolvable.start()

        return "Solution found." in solvable_out and \
               "Search stopped without finding a solution." in unsolvable_out
