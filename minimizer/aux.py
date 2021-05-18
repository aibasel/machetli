import tempfile
import contextlib
import os

from minimizer.sas_reader import sas_file_to_SASTask
from minimizer.pddl_writer import write_PDDL
from minimizer.downward_lib import pddl_parser

GENERATED_PDDL_DOMAIN_FILENAME = "generated_pddl_domain_filename"
GENERATED_PDDL_PROBLEM_FILENAME = "generated_pddl_problem_filename"
PDDL_TASK = "pddl_task"

GENERATED_SAS_FILENAME = "generated_sas_filename"
SAS_TASK = "sas_task"


def parse_pddl_task(dom_filename, prob_filename):
    """
    Returns parsed PDDL task instance.
    """
    return pddl_parser.open(domain_filename=dom_filename,
                            task_filename=prob_filename)


def parse_sas_task(task_filename):
    """
    Returns parsed SAS+ task instance.
    """
    return sas_file_to_SASTask(task_filename)


def run_all(state):
    """
    Starts all runs in *state["runs"]* and returns a dictionary where run outputs
    can be accessed the following ways: *results[run_name]["stdout]*, 
    *results[run_name]["stderr]* or *results[run_name]["returncode]*.
    """
    assert "runs" in state, "Could not find entry \"runs\" in state."
    results = {}
    for name, run in state["runs"].items():
        stdout, stderr, returncode = run.start(state)
        if run.log_always or run.log_on_fail and returncode != 0:
            if stdout:
                with open(os.path.join(state["cwd"], f"{name}.log"), "w") as logfile:
                    logfile.write(stdout)
            if stderr:
                with open(os.path.join(state["cwd"], f"{name}.err"), "w") as errfile:
                    errfile.write(stderr)
        results.update(
            {name: {"stdout": stdout, "stderr": stderr, "returncode": returncode}}
        )
    return results


def run_and_parse_all(state, parsers):
    """
    Executes *run_all(state)* and returns an updated version of the results
    dictionary containing the parsing results in place of the actual stdout
    and stderr outputs.
    """
    results = run_all(state)
    parsed_results = {}
    parsers = [parsers] if not isinstance(parsers, list) else parsers
    for name, result in results.items():
        parsed_results.update(
            {name: {"stdout": {}, "stderr": {},
                    "returncode": result["returncode"]}}
        )
        for parser in parsers:
            parsed_results[name]["stdout"].update(
                parser.parse(name, result["stdout"]))
            parsed_results[name]["stderr"].update(
                parser.parse(name, result["stderr"]))
    parsed_results["raw_results"] = results
    return parsed_results


def generate_sas_file(state):
    """
    Generates a temporary file containing the dump of the SAS+ task from 
    *state[sas_task_key]* and returns its full path. When the temporary 
    file is not needed anymore, it can be removed with *os.remove(path)* 
    (it is not removed automatically).
    """
    f = tempfile.NamedTemporaryFile(mode="w+t", suffix=".sas", delete=False)
    state[SAS_TASK].output(f)
    f.close()
    return f.name


def generate_pddl_files(state):
    """
    Generates temporary files containing the dumps of the domain and problem
    description of the PDDL task from *state[pddl_task_key]* and returns a
    tuple of the two full paths. When the temporary files are not needed
    anymore, they can both be removed with *os.remove(path)* (they are not
    removed automatically).
    """
    domain_f = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    domain_f.close()
    problem_f = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    problem_f.close()
    write_PDDL(state[PDDL_TASK], domain_filename=domain_f.name,
               problem_filename=problem_f.name)
    return (domain_f.name, problem_f.name)


@contextlib.contextmanager
def state_with_generated_sas_file(state):
    """
    Context manager that adds an entry for the temporary generated sas file
    to *state* and removes it afterwards.
    """
    state[GENERATED_SAS_FILENAME] = generate_sas_file(state)
    yield state
    # delete temporary file and delete entry from state
    os.remove(state[GENERATED_SAS_FILENAME])
    del state[GENERATED_SAS_FILENAME]


@contextlib.contextmanager
def state_with_generated_pddl_files(state):
    """
    Context manager that adds entries for the temporary generated domain
    and problem file to *state* and removes them afterwards.
    """
    domain_filename, problem_filename = generate_pddl_files(state)
    state[GENERATED_PDDL_DOMAIN_FILENAME] = domain_filename
    state[GENERATED_PDDL_PROBLEM_FILENAME] = problem_filename
    yield state
    # delete temporary files and delete entries from state
    os.remove(state[GENERATED_PDDL_DOMAIN_FILENAME])
    os.remove(state[GENERATED_PDDL_PROBLEM_FILENAME])
    del state[GENERATED_PDDL_DOMAIN_FILENAME]
    del state[GENERATED_PDDL_PROBLEM_FILENAME]
