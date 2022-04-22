from machetli import sas, tools

import constants


def evaluate(state):
    with sas.temporary_file(state) as sas_filename:

        run_reference = tools.RunWithInputFile(
            constants.get_reference_command(),
            input_file=f"{sas_filename}", time_limit=20, memory_limit=3000)
        stdout, _, _ = run_reference.start()
        cost = constants.COST_RE.search(stdout).group()

        run_mip = tools.RunWithInputFile(
            constants.get_mip_command(),
            input_file=f"{sas_filename}", time_limit=20, memory_limit=3000)
        stdout, _, _ = run_mip.start()
        initial_h = constants.INITIAL_H_RE.search(stdout).group()

        return cost < initial_h
