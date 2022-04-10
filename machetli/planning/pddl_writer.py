from machetli.planning.downward_lib.pddl import Task, Truth
from machetli.planning.downward_lib.pddl.conditions import ConstantCondition, Atom

CLOSING_BRACKET = ")"
SIN = " "  # single indentation
DIN = "  "  # double indentation


def write_domain_header(task, df):
    df.write("define (domain {})\n".format(task.domain_name))


def write_domain_requirements(task, df):
    if len(task.requirements.requirements) != 0:
        df.write(SIN + "(:requirements")
        for req in task.requirements.requirements:
            df.write(" " + req)
        df.write(")\n")


def write_domain_types(task, df):
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


def write_domain_objects(task, df):
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


def write_domain_predicates(task, df):
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


def write_domain_functions(task, df):
    if task.functions:
        df.write(SIN + "(:functions\n")
        for function in task.functions:
            function.dump_pddl(df, DIN)
        df.write(SIN + ")\n")


def write_domain_actions(task, df):
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


def write_domain_axioms(task, df):
    for axiom in task.axioms:
        df.write(SIN + "(:derived ({} ".format(axiom.name))
        for par in axiom.parameters:
            df.write("%s - %s " % (par.name, par.type_name))
        df.write(")\n")
        axiom.condition.dump_pddl(df, DIN)
        df.write(SIN + ")\n")


def write_domain_PDDL(task, domain_filename):
    with open(domain_filename, "w") as df:
        df.write("\n(")
        write_domain_header(task, df)
        write_domain_requirements(task, df)
        write_domain_types(task, df)
        write_domain_objects(task, df)
        write_domain_predicates(task, df)
        write_domain_functions(task, df)
        write_domain_axioms(task, df)
        write_domain_actions(task, df)
        df.write(")\n")


def write_problem_header(task, pf):
    pf.write("define (problem {})\n".format(task.task_name))


def write_problem_domain(task, pf):
    pf.write(SIN + "(:domain {})\n".format(task.domain_name))


def write_problem_init(task, pf):
    pf.write(SIN + "(:init\n")

    for elem in task.init:
        if isinstance(elem, Atom) and elem.predicate == "=":
            continue
        elem.dump_pddl(pf, SIN + DIN)
    pf.write(SIN + ")\n")


def write_problem_goal(task, pf):
    pf.write(SIN + "(:goal\n")
    if not isinstance(task.goal, ConstantCondition):
        task.goal.dump_pddl(pf, SIN + DIN)
    pf.write("%s)\n" % SIN)


def write_problem_metric(task, pf):
    if task.use_min_cost_metric:
        pf.write("%s(:metric minimize (total-cost))\n" % SIN)


def write_problem_PDDL(task, problem_filename):
    with open(problem_filename, "w") as pf:
        pf.write("\n(")
        write_problem_header(task, pf)
        write_problem_domain(task, pf)
        write_problem_init(task, pf)
        write_problem_goal(task, pf)
        write_problem_metric(task, pf)
        pf.write(")\n")


def write_PDDL(task: Task, domain_filename: str, problem_filename: str):
    write_domain_PDDL(task, domain_filename)
    write_problem_PDDL(task, problem_filename)
