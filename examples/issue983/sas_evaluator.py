from machetli import sas, tools
import re

import constants


def evaluate(state):
    with sas.temporary_file(state) as sas_filename:

        command_reference = [
            constants.PLANNER, "--search", constants.REFERENCE_STRING,
            "--translate-options", "--relaxed"
        ]
        run_reference = tools.RunWithInputFile(
            command_reference, input=f"{sas_filename}", time_limit=20,
            memory_limit=3000)
        stdout, _, _ = run_reference.start()
        cost = parse_cost(stdout)

        command_mip = [constants.PLANNER, "--search", constants.MIP_STRING]
        run_mip = tools.RunWithInputFile(
            command_mip, input=f"{sas_filename}", time_limit=20,
            memory_limit=3000)
        stdout, _, _ = run_mip.start()
        initial_h = parse_initial_h(stdout)

        return cost < initial_h
