from minimizer.sas_reader import sas_file_to_SASTask
from minimizer.downward_lib import pddl_parser

NEW_DOMAIN_FILENAME = "minimized-domain.pddl"
NEW_PROBLEM_FILENAME = "minimized-problem.pddl"
NEW_SAS_FILENAME = "minimized.sas"

# TODO: Handle temp files


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
            {name: {"stdout": {}, "stderr": {}, "returncode": result["returncode"]}}
        )
        for parser in parsers:
            parsed_results[name]["stdout"].update(parser.parse(name, result["stdout"]))
            parsed_results[name]["stderr"].update(parser.parse(name, result["stderr"]))
    return parsed_results
