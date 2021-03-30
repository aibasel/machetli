import minimizer.state as state_util
from minimizer.pddl_writer import write_PDDL
from minimizer.sas_reader import write_SAS
from minimizer.downward_lib import timers
import subprocess
import os
from lab.calls.call import set_limit
import resource


class Evaluator:
    def evaluate(self, state):
        raise NotImplementedError()


class Call:
    def __init__(
        self,
        args,
        name,
        time_limit=None,
        memory_limit=None,
        ipt=None,
        **kwargs
    ):

        def get_bytes(limit):
            return None if limit is None else int(limit * 1024)

        def prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                set_limit(
                    resource.RLIMIT_AS, memory_limit * 1024 * 1024, hard_mem_limit
                )
            set_limit(resource.RLIMIT_CORE, 0, 0)

        try:
            process = subprocess.Popen(args,
                                       preexec_fn=prepare_call,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE if ipt else None,
                                       text=True,
                                       **kwargs)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit(f'Error: Call {name} failed. "{args[0]}" not found.')
            else:
                raise
        except subprocess.SubprocessError as sErr:
            raise
        
        out_str, err_str = process.communicate(input=ipt)

        self.stdout = out_str
        self.stderr = err_str
        self.returncode = process.returncode


def run_call_string(state, name, parsers, ipt=None):
    if not isinstance(parsers, list):
        parsers = [parsers]
    result = {"stderr": {}}
    with timers.timing("Running successor"):
        run = state["call_strings"][name]
        tl = run["time_limit"] if "time_limit" in run else None
        ml = run["memory_limit"] if "memory_limit" in run else None
        call = Call(run["args"],
                    name,
                    time_limit=tl,
                    memory_limit=ml,
                    ipt=ipt)
        for parser in parsers:
            result.update(parser.parse(name, call.stdout))
            result["stderr"].update(parser.parse(name, call.stderr))
        result["returncode"] = call.returncode
    return result


def run_pddl_task(state, name, parsers):
    assert "pddl_task" in state, "State must contain \"pddl_task\" entry."
    state_util.update_pddl_call_strings(state)
    write_PDDL(state["pddl_task"], state_util.NEW_DOMAIN_FILENAME,
               state_util.NEW_PROBLEM_FILENAME)
    result = run_call_string(state, name, parsers)
    return result


def run_sas_task(state, name, parsers):
    assert "sas_task" in state, "State must contain \"sas_task\" entry."
    state_util.update_sas_call_strings(state)
    write_SAS(state["sas_task"], state_util.NEW_SAS_FILENAME)
    f = open(state["sas_file"], "r")
    sas_content = f.read()
    f.close()
    result = run_call_string(state, name, parsers, ipt=sas_content)
    return result
