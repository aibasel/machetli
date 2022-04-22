from machetli import pddl, tools

import constants


def evaluate(state):
    with pddl.temporary_files(state) as (domain, problem):
        print("evaluate")
        run_reference = tools.Run(
            constants.get_reference_command([domain, problem]),
            time_limit=20, memory_limit=3000)
        stdout, _, _ = run_reference.start()
        cost = constants.COST_RE.search(stdout).group()

        run_mip = tools.Run(
            constants.get_mip_command([domain, problem]),
            time_limit=20, memory_limit=3000)
        stdout, _, _ = run_mip.start()
        initial_h = constants.INITIAL_H_RE.search(stdout).group()

        return cost < initial_h
