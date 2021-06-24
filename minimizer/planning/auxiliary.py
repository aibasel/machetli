import tempfile
import contextlib
import os

from minimizer.planning.sas_reader import sas_file_to_SASTask
from minimizer.planning.pddl_writer import write_PDDL
from minimizer.planning.downward_lib import pddl_parser

GENERATED_PDDL_DOMAIN_FILENAME = "generated_pddl_domain_filename"
GENERATED_PDDL_PROBLEM_FILENAME = "generated_pddl_problem_filename"
PDDL_TASK = "pddl_task"

GENERATED_SAS_FILENAME = "generated_sas_filename"
SAS_TASK = "sas_task"


def parse_pddl_task(dom_filename, prob_filename):
    """Parse the PDDL task defined in PDDL files *dom_filename* (PDDL domain)
    and *prob_filename* (PDDL problem) an return an instance of the parsed PDDL task.

    The returned task object is an instance of the ``Task`` class used internally
    in `Fast Downward <http://www.fast-downward.org>`_.

    """
    return pddl_parser.open(domain_filename=dom_filename,
                            task_filename=prob_filename)


def parse_sas_task(task_filename):
    """Parse the SAS\ :sup:`+` task defined in the SAS\ :sup:`+` file
    *task_filename* and return an instance of the parsed SAS\ :sup:`+` task.

    The returned task object is an instance of the ``SASTask`` class used internally
    in `Fast Downward <http://www.fast-downward.org>`_.
    """
    return sas_file_to_SASTask(task_filename)


def generate_sas_file(state):
    """Generate a temporary file containing the dump of the
    SAS\ :sup:`+` task stored behind the ``"sas_task"`` key in 
    the *state* dictionary and return its file name. The file 
    is not deleted automatically.
    """
    f = tempfile.NamedTemporaryFile(mode="w+t", suffix=".sas", delete=False)
    state[SAS_TASK].output(f)
    f.close()
    return f.name


def generate_pddl_files(state):
    """Generate temporary files with the PDDL dumps of the domain and the problem
    description of the PDDL task stored behind the ``"pddl_task"`` key in the
    *state* dictionary and return a 2-tuple with the two file names in
    order ``(domain_file, problem_file)``.
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
    """Context manager that generates a temporary SAS\ :sup:`+` file
    containing the dump of the SAS\ :sup:`+` task stored behind the
    ``"sas_task"`` key in the *state* dictionary and adds a dictionary
    entry for the file name to *state*.
    
    After the context is left, the generated file is deleted,
    as well as the entry in *state*.

    For a usage example, see the context manager :func:`state_with_generated_pddl_files<state_with_generated_pddl_files>`,
    as it works analogously.
    """
    state[GENERATED_SAS_FILENAME] = generate_sas_file(state)
    yield state
    # delete temporary file and delete entry from state
    os.remove(state[GENERATED_SAS_FILENAME])
    del state[GENERATED_SAS_FILENAME]


@contextlib.contextmanager
def state_with_generated_pddl_files(state):
    """Context manager that generates temporary PDDL domain
    and problem files containing the dump of the PDDL task stored
    behind the ``"pddl_task"`` key in the *state* dictionary and
    adds dictionary entries for the file names to *state*.
    
    After the context is left, the generated files are deleted,
    as well as the entries in *state*.

    Example:

    >>> from minimizer.planning.auxiliary import state_with_generated_pddl_files, parse_pddl_task
    >>> state = {
    ...     "pddl_task": parse_pddl_task("../examples/issue335_PDDL/cntr-domain.pddl",
    ...     "../examples/issue335_PDDL/cntr-problem.pddl")
    ... }
    >>> # state does not contain the entries yet...
    >>> "generated_pddl_domain_filename" in state or "generated_pddl_problem_filename" in state
    False
    >>> # ... but inside the context manager it does:
    >>> with state_with_generated_pddl_files(state) as temp_state:
    ...     "generated_pddl_domain_filename" in temp_state and 
    ...     "generated_pddl_problem_filename" in temp_state
    ...
    True
    >>> # The generated files in the state dictionary can now be used to replace placeholders in commands,
    >>> # like in:
    >>> cmd = ["fast-downward.py", "{generated_pddl_domain_filename}", "{generated_pddl_problem_filename}",
    ... "--search", "astar(lmcut())"]
    >>> with state_with_generated_pddl_files(state) as temp_state:
    ...     formatted_cmd = [part.format(**temp_state) for part in cmd]
    ...

    Functions *run_all* and *run_and_parse_all* automatically do this
    command formatting before executing runs and expect the state passed
    as their argument contain entries for the keys
    ``"generated_pddl_domain_filename"`` and ``"generated_pddl_problem_filename"``.
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
