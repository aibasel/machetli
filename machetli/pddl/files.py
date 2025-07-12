import logging
from pathlib import Path
from pickle import PickleError
import sys
from typing import Union

from machetli.pddl.constants import KEY_IN_STATE
from machetli.pddl.downward import pddl_parser
from machetli.pddl.downward.pddl import Truth
from machetli.pddl.downward.pddl.conditions import ConstantCondition, Atom

from machetli import tools
from machetli.evaluator import EXIT_CODE_CRITICAL, EXIT_CODE_BEHAVIOR_PRESENT, \
    EXIT_CODE_BEHAVIOR_NOT_PRESENT

SIN = " "  # single indentation
DIN = "  "  # double indentation


def find_domain_path(task_path: Path):
    """
    Find domain path for the given task using automatic naming rules.
    """
    domain_basenames = [
        "domain.pddl",
        task_path.stem + "-domain" + task_path.suffix,
        task_path.name[:3] + "-domain.pddl",  # for airport
        "domain_" + task_path.name,
        "domain-" + task_path.name,
    ]

    for domain_basename in domain_basenames:
        domain_path = task_path.parent / domain_basename
        if domain_path.exists():
            return domain_path


def generate_initial_state(domain_path: Union[Path, str],
                           task_path: Union[Path, str]) -> dict:
    """
    Parse the PDDL task defined in the given PDDL files. 

    :return: a dictionary pointing to the task specified in the files.
    """
    return {
        KEY_IN_STATE: pddl_parser.open(domain_filename=domain_path,
                                       task_filename=task_path)
    }


def _run_evaluator_on_pddl_files(evaluate, domain_filename, task_filename):
    """
    Run the given function *evaluate* and exit with the appropriate exit code.
    If the function returns ``True``, use
    :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>`,
    otherwise use
    :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_NOT_PRESENT>`.

    :param evaluate: is a function taking filenames of a PDDL domain and problem
        file as input and returning ``True`` if the specified behavior occurs
        for the given instance, and ``False`` if it doesn't. Other ways of
        exiting the function (exceptions, ``sys.exit`` with exit codes other than
        :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>` or
        :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_NOT_PRESENT>`)
        are treated as failed evaluations by the search.
    :param domain_filename: is the filename of a PDDL domain file.
    :param task_filename: is the filename of a PDDL problem file.
    """
    if evaluate(domain_filename, task_filename):
        sys.exit(EXIT_CODE_BEHAVIOR_PRESENT)
    else:
        sys.exit(EXIT_CODE_BEHAVIOR_NOT_PRESENT)


def run_evaluator(evaluate):
    """
    Load the state passed to the script via its command line arguments, then run
    the given function *evaluate* on the domain and problem encoded in the
    state, and exit the program with the appropriate exit code. If the function
    returns ``True``, use
    :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>`,
    otherwise use
    :attr:`EXIT_CODE_NOT_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_NOT_BEHAVIOR_PRESENT>`.
    In addition to running the evaluator, this function creates the PDDL files as
    'domain.pddl' and 'problem.pddl' in the current directory.

    This function is meant to be used as the main function of an evaluator
    script. Instead of a path to the state, the command line arguments can also
    be paths to a PDDL domain and problem (where the domain can be omitted if it
    can be found with automated naming rules). This is meant for testing and
    debugging the evaluator directly on PDDL input.

    :param evaluate: is a function taking filenames of a PDDL domain and problem
        file as input and returning ``True`` if the specified behavior occurs
        for the given instance, and ``False`` if it doesn't. Other ways of
        exiting the function (exceptions, ``sys.exit`` with exit codes other than
        :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>` or
        :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_NOT_PRESENT>`)
        are treated as failed evaluations by the search.
    """
    filenames = sys.argv[1:]
    if len(filenames) == 1:
        try:
            state = tools.read_state(filenames[0])
            write_files(state, "domain.pddl", "problem.pddl")
            _run_evaluator_on_pddl_files(evaluate, "domain.pddl", "problem.pddl")
        except (FileNotFoundError, PickleError):
            task_path = Path(filenames[0])
            domain_path = find_domain_path(task_path)
            if domain_path is None:
                logging.critical(
                    "Error: Could not find domain file using automatic naming rules.")
            _run_evaluator_on_pddl_files(evaluate, domain_path, task_path)
    elif len(filenames) == 2:
        domain_filename, task_filename = filenames
        _run_evaluator_on_pddl_files(evaluate, domain_filename, task_filename)
    else:
        logging.critical(
            "Error: evaluator has to be called with either a path to a pickled "
            "state, a task filename, or a domain filename followed by a task "
            "filename.")
        sys.exit(EXIT_CODE_CRITICAL)


def _write_domain_header(task, file):
    file.write("define (domain {})\n".format(task.domain_name))


def _write_domain_requirements(task, file):
    if len(task.requirements.requirements) != 0:
        file.write(SIN + "(:requirements")
        for req in task.requirements.requirements:
            file.write(" " + req)
        file.write(")\n")


def _write_domain_types(task, file):
    if task.types:
        file.write(SIN + "(:types\n")
        types_dict = {}
        for tp in task.types:  # build dictionary of base types and types
            if tp.basetype_name is not None:
                if tp.basetype_name not in types_dict:
                    types_dict[tp.basetype_name] = [tp.name]
                else:
                    types_dict[tp.basetype_name].append(tp.name)
        for basetype in types_dict:
            file.write(SIN + DIN)
            for name in types_dict[basetype]:
                file.write(name + " ")
            file.write("- " + basetype + "\n")
        file.write(SIN + ")\n")


def _write_domain_objects(task, file):
    if task.objects:  # all objects from planning task are going to be written into constants
        file.write(SIN + "(:constants\n")
        objects_dict = {}
        for obj in task.objects:  # build dictionary of object type names and object names
            if obj.type_name not in objects_dict:
                objects_dict[obj.type_name] = [obj.name]
            else:
                objects_dict[obj.type_name].append(obj.name)
        for type_name in objects_dict:
            file.write(SIN + DIN)
            for name in objects_dict[type_name]:
                file.write(name + " ")
            file.write("- " + type_name + "\n")
        file.write(SIN + ")\n")


def _write_domain_predicates(task, file):
    if len(task.predicates) != 0:
        file.write(SIN + "(:predicates\n")
        for pred in task.predicates:
            if pred.name == "=":
                continue
            types_dict = {}
            for arg in pred.arguments:
                if arg.type_name not in types_dict:
                    types_dict[arg.type_name] = [arg.name]
                else:
                    types_dict[arg.type_name].append(arg.name)
            file.write(SIN + SIN + "(" + pred.name)
            for obj in types_dict:
                for name in types_dict[obj]:
                    file.write(" " + name)
                file.write(" - " + obj)
            file.write(")\n")
        file.write(SIN + ")\n")


def _write_domain_functions(task, file):
    if task.functions:
        file.write(SIN + "(:functions\n")
        for function in task.functions:
            function.dump_pddl(file, DIN)
        file.write(SIN + ")\n")


def _write_domain_actions(task, file):
    for action in task.actions:
        file.write(SIN + "(:action {}\n".format(action.name))

        file.write(DIN + ":parameters (")
        if action.parameters:
            for par in action.parameters:
                file.write("%s - %s " % (par.name, par.type_name))
        file.write(")\n")

        file.write(SIN + SIN + ":precondition\n")
        if not isinstance(action.precondition, Truth):
            action.precondition.dump_pddl(file, DIN)
        file.write(DIN + ":effect\n")
        file.write(DIN + "(and\n")
        for eff in action.effects:
            eff.dump_pddl(file, DIN)
        if action.cost:
            action.cost.dump_pddl(file, DIN + DIN)
        file.write(DIN + ")\n")

        file.write(SIN + ")\n")


def _write_domain_axioms(task, file):
    for axiom in task.axioms:
        file.write(SIN + "(:derived ({} ".format(axiom.name))
        for par in axiom.parameters:
            file.write("%s - %s " % (par.name, par.type_name))
        file.write(")\n")
        axiom.condition.dump_pddl(file, DIN)
        file.write(SIN + ")\n")


def _write_domain(task, path: Path):
    with path.open("w") as file:
        file.write("\n(")
        _write_domain_header(task, file)
        _write_domain_requirements(task, file)
        _write_domain_types(task, file)
        _write_domain_objects(task, file)
        _write_domain_predicates(task, file)
        _write_domain_functions(task, file)
        _write_domain_axioms(task, file)
        _write_domain_actions(task, file)
        file.write(")\n")


def _write_problem_header(task, file):
    file.write("define (problem {})\n".format(task.task_name))


def _write_problem_domain(task, file):
    file.write(SIN + "(:domain {})\n".format(task.domain_name))


def _write_problem_init(task, file):
    file.write(SIN + "(:init\n")

    for elem in task.init:
        if isinstance(elem, Atom) and elem.predicate == "=":
            continue
        elem.dump_pddl(file, SIN + DIN)
    file.write(SIN + ")\n")


def _write_problem_goal(task, file):
    file.write(SIN + "(:goal\n")
    if not isinstance(task.goal, ConstantCondition):
        task.goal.dump_pddl(file, SIN + DIN)
    file.write("%s)\n" % SIN)


def _write_problem_metric(task, file):
    if task.use_min_cost_metric:
        file.write("%s(:metric minimize (total-cost))\n" % SIN)


def _write_problem(task, path: Path):
    with path.open("w") as file:
        file.write("\n(")
        _write_problem_header(task, file)
        _write_problem_domain(task, file)
        _write_problem_init(task, file)
        _write_problem_goal(task, file)
        _write_problem_metric(task, file)
        file.write(")\n")


def write_files(state: dict, domain_path: Union[Path, str],
                problem_path: Union[Path, str]):
    """
    Write the domain and problem files represented in `state` to disk.
    """
    _write_domain(state[KEY_IN_STATE], Path(domain_path))
    _write_problem(state[KEY_IN_STATE], Path(problem_path))
