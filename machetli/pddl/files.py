import tempfile
import contextlib
import os

from machetli.pddl.constants import KEY_IN_STATE
from machetli.pddl.downward import pddl_parser
from machetli.pddl.downward.pddl import Truth
from machetli.pddl.downward.pddl.conditions import ConstantCondition, Atom

SIN = " "  # single indentation
DIN = "  "  # double indentation


def generate_initial_state(domain_filename: str, problem_filename: str) -> dict:
    """
    Parse the PDDL task defined in PDDL files `domain_filename` (PDDL
    domain) and `problem_filename` (PDDL problem) and return an initial
    state containing the parsed PDDL task.

    :return: a dictionary pointing to the PDDL task specified in the
             files `domain_filename` and `problem_filename`.
    """
    return {
        KEY_IN_STATE: pddl_parser.open(domain_filename=domain_filename,
                                       task_filename=problem_filename)
    }


@contextlib.contextmanager
def temporary_files(state: dict) -> tuple:
    """
    Context manager that generates temporary PDDL files containing the
    task stored in the `state` dictionary. After the context is left,
    the generated files are deleted.

    Example:

    .. code-block:: python

        with temporary_files(state) as domain, problem:
            cmd = ["fast-downward.py", f"{domain}", f"{problem}", "--search", "astar(lmcut())"]

    :return: a tuple containing domain and problem filename.
    """
    domain_file = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    domain_file.close()
    problem_file = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    problem_file.close()
    write_files(state, domain_filename=domain_file.name,
                problem_filename=problem_file.name)
    yield domain_file.name, problem_file.name
    os.remove(domain_file.name)
    os.remove(problem_file.name)


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


def _write_domain(task, filename):
    with open(filename, "w") as file:
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


def _write_problem(task, filename):
    with open(filename, "w") as file:
        file.write("\n(")
        _write_problem_header(task, file)
        _write_problem_domain(task, file)
        _write_problem_init(task, file)
        _write_problem_goal(task, file)
        _write_problem_metric(task, file)
        file.write(")\n")


def write_files(state: dict, domain_filename: str, problem_filename: str):
    """
    Write the domain and problem files represented in `state` to disk.
    """
    _write_domain(state[KEY_IN_STATE], domain_filename)
    _write_problem(state[KEY_IN_STATE], problem_filename)
