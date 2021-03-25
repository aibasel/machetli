import minimizer.state as state_util
from minimizer.pddl_writer import write_PDDL
from minimizer.sas_reader import write_SAS
from minimizer.downward_lib import timers
import subprocess
import os


class Evaluator():
    def evaluate(self, state):
        raise NotImplementedError()


def run_call_string(state, call_string, parsers, ipt=None):
    if not isinstance(parsers, list):
        parsers = [parsers]
    result = {}
    with timers.timing("Running successor"):
        cmd = state["call_strings"][call_string]
        output = subprocess.run(cmd,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                input=ipt).stdout
        for parser in parsers:
            result.update(parser.parse(call_string, output))
    return result


def run_pddl_task(state, call_string, parsers):
    assert "pddl_task" in state, "State must contain \"pddl_task\" entry."
    state_util.update_pddl_call_strings(state)
    write_PDDL(state["pddl_task"], state_util.NEW_DOMAIN_FILENAME,
               state_util.NEW_PROBLEM_FILENAME)
    result = run_call_string(state, call_string, parsers)
    return result


def run_sas_task(state, call_string, parsers):
    assert "sas_task" in state, "State must contain \"sas_task\" entry."
    state_util.update_sas_call_strings(state)
    write_SAS(state["sas_task"], state_util.NEW_SAS_FILENAME)
    f = open(state["sas_file"], "r")
    sas_content = f.read()
    f.close()
    result = run_call_string(state, call_string, parsers, ipt=sas_content)
    return result
