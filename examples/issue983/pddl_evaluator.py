from machetli import pddl, tools

import constants


def evaluate(state):
    with pddl.temporary_files(state) as (domain, problem):
        print("evaluate")
        command_reference = [
            constants.PLANNER, domain, problem, "--search",
            constants.REFERENCE_STRING, "--translate-options", "--relaxed"
        ]
        run_reference = tools.Run(command_reference, time_limit=20,
                                  memory_limit=3000)
        stdout, _, _ = run_reference.start()
        cost = constants.COST_RE.search(stdout).group()

        command_mip = [
            constants.PLANNER, domain, problem, "--search",
            constants.MIP_STRING,
        ]
        run_mip = tools.Run(command_mip, time_limit=20, memory_limit=3000)
        stdout, _, _ = run_mip.start()
        initial_h = constants.INITIAL_H_RE.search(stdout).group()

        return cost < initial_h
