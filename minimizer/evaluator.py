import minimizer.state as state_util
from minimizer.pddl_writer import write_PDDL
from minimizer.sas_reader import write_SAS
import subprocess
import os


class Evaluator():
    def evaluate(self, state):
        pass


def run_commands(state, parsers):
    if not isinstance(parsers, list):
        parsers = [parsers]
    results = {}
    for cmd_name, cmd in list(state["call_strings"].items()):
        output = subprocess.run(cmd,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT).stdout
        results[cmd_name] = {}
        for parser in parsers:
            results[cmd_name].update(parser.parse(cmd_name, output))
    return results


# uses run_commands, but takes care of the rest regarding pddl tasks
def run_pddl_tasks(state, parsers):
    if "pddl_task" not in state:  # make sure that after execution of run_pddl_tasks "pddl_task" is stored in state
        state["pddl_task"] = state_util.get_pddl_task(state)
    state_util.update_pddl_call_strings(state)
    write_PDDL(state["pddl_task"], state_util.NEW_DOMAIN_FILENAME, state_util.NEW_PROBLEM_FILENAME)
    results = run_commands(state, parsers)
    deletable_files = ["output.sas"]
    for file in deletable_files:
        if os.path.exists(file):
            os.remove(file)
    return results


def run_sas_tasks(state, parsers):
    if "sas_task" not in state:  # make sure that after execution of run_sas_tasks "sas_task" is stored in state
        state["sas_task"] = state_util.get_sas_task(state)
    state_util.update_sas_call_strings(state)
    write_SAS(state["sas_task"], state_util.NEW_SAS_FILENAME)
    return run_commands(state, parser)


