import argparse

from min_problem import MinimizationProblem, PDDLMinimizationProblem, SASMinimizationProblem
from pddl_writer import write_PDDL


def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--problem", metavar="PROBLEM", required=True, nargs='+',
                           help="string representing program call that produces bug (embedded in quotes); if two are "
                                "provided, the second one acts as a reference and also requires a CHARACTERISTIC "
                                "argument")
    argparser.add_argument("--characteristic", metavar="CHARACTERISTIC", nargs='+',
                           help="string specifying characteristic or Python file that "
                                "implements parser interface", required=True)
    argparser.add_argument("--delete", help="task element to be deleted", metavar="OPTION", nargs='+',
                           required=True)
    argparser.add_argument("--falsity",
                           help="flag if atoms containing the deleted predicate should be replaced with falsity",
                           required=False, action="store_true")
    argparser.add_argument("--truth",
                           help="flag if atoms containing the deleted predicate should be replaced with truth",
                           required=False, action="store_true")
    argparser.add_argument("--write-summary",
                           help="flag if summary of transformations is desired in form of a text file",
                           required=False, action="store_true")
    return argparser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    minimization_problem = MinimizationProblem(args)
    if minimization_problem.call_string_manager.pddl_problem:
        minimization_problem = PDDLMinimizationProblem(args)
        smaller_task = minimization_problem.minimize()
        write_PDDL(smaller_task, "minimized-domain.pddl", "minimized-problem.pddl")
    else:
        minimization_problem = SASMinimizationProblem(args)
        smaller_task = minimization_problem.minimize()
        with open("minimized.sas", "w") as out_file:
            smaller_task.output(out_file)
