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
    domain_f = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    domain_f.close()
    problem_f = tempfile.NamedTemporaryFile(
        mode="w+t", suffix=".pddl", delete=False)
    problem_f.close()
    write_files(state, domain_filename=domain_f.name,
                problem_filename=problem_f.name)
    yield domain_f.name, problem_f.name
    os.remove(domain_f.name)
    os.remove(problem_f.name)


def _write_domain_header(task, df):
    df.write("define (domain {})\n".format(task.domain_name))


def _write_domain_requirements(task, df):
    if len(task.requirements.requirements) != 0:
        df.write(SIN + "(:requirements")
        for req in task.requirements.requirements:
            df.write(" " + req)
        df.write(")\n")


def _write_domain_types(task, df):
    if task.types:
        df.write(SIN + "(:types\n")
        types_dict = {}
        for tp in task.types:  # build dictionary of base types and types
            if tp.basetype_name is not None:
                if tp.basetype_name not in types_dict:
                    types_dict[tp.basetype_name] = [tp.name]
                else:
                    types_dict[tp.basetype_name].append(tp.name)
        for basetype in types_dict:
            df.write(SIN + DIN)
            for name in types_dict[basetype]:
                df.write(name + " ")
            df.write("- " + basetype + "\n")
        df.write(SIN + ")\n")


def _write_domain_objects(task, df):
    if task.objects:  # all objects from planning task are going to be written into constants
        df.write(SIN + "(:constants\n")
        objects_dict = {}
        for obj in task.objects:  # build dictionary of object type names and object names
            if obj.type_name not in objects_dict:
                objects_dict[obj.type_name] = [obj.name]
            else:
                objects_dict[obj.type_name].append(obj.name)
        for type_name in objects_dict:
            df.write(SIN + DIN)
            for name in objects_dict[type_name]:
                df.write(name + " ")
            df.write("- " + type_name + "\n")
        df.write(SIN + ")\n")


def _write_domain_predicates(task, df):
    if len(task.predicates) != 0:
        df.write(SIN + "(:predicates\n")
        for pred in task.predicates:
            if pred.name == "=":
                continue
            types_dict = {}
            for arg in pred.arguments:
                if arg.type_name not in types_dict:
                    types_dict[arg.type_name] = [arg.name]
                else:
                    types_dict[arg.type_name].append(arg.name)
            df.write(SIN + SIN + "(" + pred.name)
            for obj in types_dict:
                for name in types_dict[obj]:
                    df.write(" " + name)
                df.write(" - " + obj)
            df.write(")\n")
        df.write(SIN + ")\n")


def _write_domain_functions(task, df):
    if task.functions:
        df.write(SIN + "(:functions\n")
        for function in task.functions:
            function.dump_pddl(df, DIN)
        df.write(SIN + ")\n")


def _write_domain_actions(task, df):
    for action in task.actions:
        df.write(SIN + "(:action {}\n".format(action.name))

        df.write(DIN + ":parameters (")
        if action.parameters:
            for par in action.parameters:
                df.write("%s - %s " % (par.name, par.type_name))
        df.write(")\n")

        df.write(SIN + SIN + ":precondition\n")
        if not isinstance(action.precondition, Truth):
            action.precondition.dump_pddl(df, DIN)
        df.write(DIN + ":effect\n")
        df.write(DIN + "(and\n")
        for eff in action.effects:
            eff.dump_pddl(df, DIN)
        if action.cost:
            action.cost.dump_pddl(df, DIN + DIN)
        df.write(DIN + ")\n")

        df.write(SIN + ")\n")


def _write_domain_axioms(task, df):
    for axiom in task.axioms:
        df.write(SIN + "(:derived ({} ".format(axiom.name))
        for par in axiom.parameters:
            df.write("%s - %s " % (par.name, par.type_name))
        df.write(")\n")
        axiom.condition.dump_pddl(df, DIN)
        df.write(SIN + ")\n")


def _write_domain(task, domain_filename):
    with open(domain_filename, "w") as df:
        df.write("\n(")
        _write_domain_header(task, df)
        _write_domain_requirements(task, df)
        _write_domain_types(task, df)
        _write_domain_objects(task, df)
        _write_domain_predicates(task, df)
        _write_domain_functions(task, df)
        _write_domain_axioms(task, df)
        _write_domain_actions(task, df)
        df.write(")\n")


def _write_problem_header(task, pf):
    pf.write("define (problem {})\n".format(task.task_name))


def _write_problem_domain(task, pf):
    pf.write(SIN + "(:domain {})\n".format(task.domain_name))


def _write_problem_init(task, pf):
    pf.write(SIN + "(:init\n")

    for elem in task.init:
        if isinstance(elem, Atom) and elem.predicate == "=":
            continue
        elem.dump_pddl(pf, SIN + DIN)
    pf.write(SIN + ")\n")


def _write_problem_goal(task, pf):
    pf.write(SIN + "(:goal\n")
    if not isinstance(task.goal, ConstantCondition):
        task.goal.dump_pddl(pf, SIN + DIN)
    pf.write("%s)\n" % SIN)


def _write_problem_metric(task, pf):
    if task.use_min_cost_metric:
        pf.write("%s(:metric minimize (total-cost))\n" % SIN)


def _write_problem(task, problem_filename):
    with open(problem_filename, "w") as pf:
        pf.write("\n(")
        _write_problem_header(task, pf)
        _write_problem_domain(task, pf)
        _write_problem_init(task, pf)
        _write_problem_goal(task, pf)
        _write_problem_metric(task, pf)
        pf.write(")\n")


def write_files(state: dict, domain_filename: str, problem_filename: str):
    """
    Write the domain and problem files represented in `state` to disk.
    """
    _write_domain(state[KEY_IN_STATE], domain_filename)
    _write_problem(state[KEY_IN_STATE], problem_filename)
