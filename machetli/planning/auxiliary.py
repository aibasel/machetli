import tempfile
import contextlib
import os

from machetli.planning.sas_reader import sas_file_to_SASTask
from machetli.planning.pddl_writer import write_PDDL
from machetli.planning.downward_lib import pddl_parser

PDDL_TASK = "pddl_task"
SAS_TASK = "sas_task"


def parse_pddl_task(dom_filename, prob_filename):
    """Parse the PDDL task defined in PDDL files *dom_filename* (PDDL domain)
    and *prob_filename* (PDDL problem) an return an instance of the parsed PDDL task.

    The returned task object is an instance of the ``Task`` class used internally
    in `Fast Downward <https://www.fast-downward.org>`_.

    """
    return pddl_parser.open(domain_filename=dom_filename,
                            task_filename=prob_filename)


def parse_sas_task(task_filename):
    """Parse the SAS\ :sup:`+` task defined in the SAS\ :sup:`+` file
    *task_filename* and return an instance of the parsed SAS\ :sup:`+` task.

    The returned task object is an instance of the ``SASTask`` class used internally
    in `Fast Downward <https://www.fast-downward.org>`_.
    """
    return sas_file_to_SASTask(task_filename)

@contextlib.contextmanager
def generated_sas_file(state):
    """Context manager that generates a temporary SAS\ :sup:`+` file
    containing the task stored under the ``"sas_task"`` key in the *state*
    dictionary. After the context is left, the generated file is deleted.

    Example:

    >>> with generated_sas_file(state) as sas_filename:
    ...     cmd = ["fast-downward.py", f"{sas_filename}", "--search", "astar(lmcut())"]
    ...
    """
    f = tempfile.NamedTemporaryFile(mode="w+t", suffix=".sas", delete=False)
    state[SAS_TASK].output(f)
    f.close()
    yield f.name
    os.remove(f.name)

@contextlib.contextmanager
def generated_pddl_files(state):
    """Context manager that generates temporary PDDL files
    containing the task stored under the ``"pddl_task"`` key in the *state*
    dictionary. After the context is left, the generated files are deleted.

    Example:

    >>> with generated_pddl_files(state) as (domain_filename, problem_filename):
    ...     cmd = ["fast-downward.py", f"{domain_filename}", f"{problem_filename}", "--search", "astar(lmcut())"]
    ...
    """
    domain_f = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    domain_f.close()
    problem_f = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    problem_f.close()
    write_PDDL(state[PDDL_TASK], domain_filename=domain_f.name,
               problem_filename=problem_f.name)
    yield (domain_f.name, problem_f.name)
    os.remove(domain_f.name)
    os.remove(problem_f.name)
