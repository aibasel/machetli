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


def generate_sas_file(state):
    """Generates and returns a temporary SAS+ file from the SAS+ task in `state`.

    Generates a temporary file (inside the ``/tmp`` directory) with the task dump of the SAS+ task in ``state["sas_task"]`` and returns its file name. When the temporary 
    file is not needed anymore, it should be removed with ``os.remove(filename)`` because it is not removed automatically.

    Parameters
    ----------
    state : dict
        The dictionary describing an instance of the minimization problem.

    Returns
    -------
    str
        The filename.
    """
    f = tempfile.NamedTemporaryFile(mode="w+t", suffix=".sas", delete=False)
    state[SAS_TASK].output(f)
    f.close()
    return f.name


def generate_pddl_files(state):
    """Generates and returns temporary PDDL files from the PDDL task in `state`.

    Generates temporary files (inside the ``/tmp`` directory) with the PDDL dumps of the domain and the problem
    of the PDDL task in ``state["pddl_task"]`` and returns a
    tuple containing the two files.
    When the temporary files are not needed
    anymore, they should both be removed with ``os.remove(filename)`` because they are not removed automatically.

    Parameters
    ----------
    state : dict
        The dictionary describing an instance of the minimization problem.

    Returns
    -------
    2-tuple of str
        The two filenames. Order: ``(domain_file, problem_file)``.
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
