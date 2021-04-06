import tempfile
import contextlib
import os

from minimizer.sas_reader import sas_file_to_SASTask
from minimizer.pddl_writer import write_PDDL
from minimizer.downward_lib import pddl_parser


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
    return parsed_results


def generate_sas_file(state, sas_task_key="sas_task"):
    """
    Generates a temporary file containing the dump of the SAS+ task from 
    *state[sas_task_key]* and returns its full path. When the temporary 
    file is not needed anymore, it can be removed with *os.remove(path)* 
    (it is not removed automatically).
    """
    f = tempfile.NamedTemporaryFile(mode="w+t", suffix=".sas", delete=False)
    state[sas_task_key].output(f)
    f.close()
    return f.name


def generate_pddl_files(state, pddl_task_key="pddl_task"):
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
    write_PDDL(state[pddl_task_key], domain_filename=domain_f.name,
               problem_filename=problem_f.name)
    return (domain_f.name, problem_f.name)


@contextlib.contextmanager
def state_with_generated_sas_file(state, sas_file_key="generated_sas_filename", sas_task_key="sas_task"):
    """
    Context manager that adds an entry for the temporary generated sas file
    to *state* and removes it afterwards.
    """
    # TODO: not sure if modifying the state object directly is a good idea
    state[sas_file_key] = generate_sas_file(state, sas_task_key)
    yield state
    # delete temporary file and delete entry from state
    os.remove(state[sas_file_key])
    del state[sas_file_key]


@contextlib.contextmanager
def state_with_generated_pddl_files(state,
                                    pddl_domain_key="generated_pddl_domain_filename",
                                    pddl_problem_key="generated_pddl_problem_filename",
                                    pddl_task_key="pddl_task"):
    """
    Context manager that adds entries for the temporary generated domain
    and problem file to *state* and removes it afterwards.
    """
    domain_filename, problem_filename = generate_pddl_files(state, pddl_task_key)
    # TODO: not sure if modifying the state object directly is a good idea
    state[pddl_domain_key] = domain_filename
    state[pddl_problem_key] = problem_filename
    yield state
    # delete temporary files and delete entries from state
    os.remove(state[pddl_domain_key])
    os.remove(state[pddl_problem_key])
    del state[pddl_domain_key]
    del state[pddl_problem_key]
