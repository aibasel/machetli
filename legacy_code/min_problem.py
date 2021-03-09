import importlib.util
import sys
import subprocess

from call_string_manager import CallStringManager
from fd_19_12_modules.pddl import Task
from pddl_writer import write_PDDL
from fd_19_12_modules import pddl_parser, timers
from sas_reader import sas_file_to_SASTask
from transform_pddl import Transformer, ActionEraser, LiteralTruthReplacer, AtomTruthReplacer, ObjectEraser, \
    AtomFalsityReplacer
from transform_sas import SASOperatorEraser, SASVariableEraser


class RunnableProblem:
    """Interface for storing, running and handling planner executions."""

    def __init__(self):
        self.call_string_manager = None
        self.parser = None
        self.characteristic = None
        self._planner_type = None
        raise NotImplementedError("This class is meant to be implemented.")

    def run(self):
        completed_process = subprocess.run(self.call_string_manager.call_string,
                                           text=True, capture_output=True, shell=True)
        return completed_process

    def has_characteristic(self) -> bool:
        with timers.timing("Running {} planner".format(self._planner_type)):
            completed_process = self.run()
        stout = completed_process.stdout if completed_process.stdout is not None else ""
        sterr = completed_process.stderr if completed_process.stderr is not None else ""
        combined_process_output = stout + sterr

        if self.parser is not None:
            return self.parser.parse_output_string(combined_process_output)
        return self.characteristic in combined_process_output

    def extract_parser(self, path):
        parser_path = path
        module_name = "parser"
        spec = importlib.util.spec_from_file_location(module_name, parser_path)
        parser_module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = parser_module
        spec.loader.exec_module(parser_module)
        Parser = getattr(parser_module, "Parser")
        return Parser()


class ReferencePlanner(RunnableProblem):
    def __init__(self, args):
        self._planner_type = "reference"
        self.call_string_manager = CallStringManager(args.problem[1])
        assert len(args.characteristic) == 2, "Characteristic for reference planner must be provided as argument"
        self.characteristic = args.characteristic[1]
        self.parser = self.extract_parser(self.characteristic) if self.characteristic.split(".")[-1] == "py" else None


class MinimizationProblem(RunnableProblem):
    def __init__(self, args):
        self._planner_type = "main"
        self.delete_options = args.delete
        self.falsity = True if args.falsity else False
        self.truth = True if args.truth else False
        self.summary = True if args.write_summary else False
        assert not (self.falsity and self.truth), "--truth and --falsity cannot both be set at the same time"
        self.reference_planner = ReferencePlanner(args) if len(args.problem) == 2 else None
        self.call_string_manager = CallStringManager(args.problem[0])
        self.characteristic = args.characteristic[0]
        self.parser = self.extract_parser(self.characteristic) if self.characteristic.split(".")[-1] == "py" else None


class PDDLMinimizationProblem(MinimizationProblem):
    def minimize(self) -> Task:  # hill-climbing algorithm
        """Shrinks and returns PDDL tasks using first-choice hill-climbing."""
        domain_path = self.call_string_manager.call_string_list[self.call_string_manager.indices[0]]
        problem_path = self.call_string_manager.call_string_list[self.call_string_manager.indices[1]]
        pddl_task = pddl_parser.open(domain_filename=domain_path, task_filename=problem_path)
        new_domain_filename = "minimized-domain.pddl"
        new_problem_filename = "minimized-problem.pddl"
        write_PDDL(pddl_task, new_domain_filename, new_problem_filename)
        self.call_string_manager.replace_pddl(new_domain_filename, new_problem_filename)
        if self.reference_planner is not None:
            self.reference_planner.call_string_manager.replace_pddl(new_domain_filename, new_problem_filename)
        optional_reference_condition = True
        trafo_list = []

        with timers.timing("Starting minimization"):
            for delete_option in self.delete_options:
                removed_list = [delete_option]
                print()
                if delete_option == "action":
                    transformer = ActionEraser()
                elif delete_option == "predicate":
                    if self.falsity:
                        transformer = AtomFalsityReplacer()
                    elif self.truth:
                        transformer = AtomTruthReplacer()
                    else:
                        transformer = LiteralTruthReplacer()
                elif delete_option == "object":
                    transformer = ObjectEraser()
                else:
                    err_message = delete_option + " is not a valid option"
                    sys.exit(err_message)
                with timers.timing("Minimizing problem by deleting {}s".format(delete_option)):
                    current = pddl_parser.open(domain_filename=new_domain_filename, task_filename=new_problem_filename)
                    children = 0
                    num_successors = 0
                    print()
                    while True:
                        if children > 0:
                            print(
                                "child found ({}), searched through {} successor(s)\n".format(children, num_successors))
                        num_successors = 0
                        children += 1
                        for successor, removed_element in transformer.get_successors(current):
                            num_successors += 1
                            write_PDDL(successor, new_domain_filename, new_problem_filename)
                            if self.reference_planner is not None:
                                optional_reference_condition = self.reference_planner.has_characteristic()
                            if self.has_characteristic() and optional_reference_condition:
                                current = successor
                                removed_list.append(removed_element)
                                break  # successor selected by first choice
                        else:
                            print("No child found, end of hill climbing.")
                            trafo_list.append(removed_list)
                            write_PDDL(current, new_domain_filename, new_problem_filename)
                            pddl_task.predicates = [pred for pred in pddl_task.predicates if not pred.name == "="]
                            current.predicates = [pred for pred in current.predicates if not pred.name == "="]
                            print(
                                "\nBefore -> After:\nPredicates: {} -> {}\nActions: {} -> {}\nObjects: {} -> {}\n".format(
                                    len(pddl_task.predicates), len(current.predicates), len(pddl_task.actions),
                                    len(current.actions),
                                    len(pddl_task.objects), len(current.objects)))
                            break
        if self.summary:
            with open("summary.txt", "w") as file:
                for option in trafo_list:  # option is list of removed elements
                    file.write("Removed {}s:\n".format(option[0]))
                    for element in option[1:]:
                        file.write("{}\n".format(str(element)))
                    file.write("\n")

        return pddl_parser.open(domain_filename=new_domain_filename, task_filename=new_problem_filename)


class SASMinimizationProblem(MinimizationProblem):
    def minimize(self):
        """Shrinks and returns SAS+ tasks using first-choice hill-climbing."""
        sas_path = self.call_string_manager.call_string_list[self.call_string_manager.indices[0]]
        sas_task = sas_file_to_SASTask(sas_path)
        new_filename = "minimized.sas"
        with open(new_filename, "w") as file:
            sas_task.output(file)  # now we have a copy of the problem we can work with
        self.call_string_manager.replace_sas(new_filename)
        trafo_list = []

        with timers.timing("Starting minimization"):
            for delete_option in self.delete_options:
                removed_list = [delete_option]
                print()
                if delete_option == "operator":
                    transformer = SASOperatorEraser()
                elif delete_option == "variable":
                    transformer = SASVariableEraser()
                else:
                    err_message = delete_option + " is not a valid option"
                    sys.exit(err_message)
                with timers.timing("Minimizing problem by deleting {}s".format(delete_option)):
                    current = sas_file_to_SASTask(new_filename)
                    children = 0
                    num_successors = 0
                    print()
                    while True:
                        if children > 0:
                            print(
                                "child found ({}), searched through {} successor(s)\n".format(children, num_successors))
                        num_successors = 0
                        children += 1
                        for successor, removed_element in transformer.get_successors(current):
                            num_successors += 1
                            with open(new_filename, "w") as file:
                                successor.output(file)
                            if self.has_characteristic():
                                current = successor
                                removed_list.append(removed_element)
                                break
                        else:
                            print("No child found, end of hill climbing.")
                            trafo_list.append(removed_list)
                            with open(new_filename, "w") as temp_file:
                                current.output(temp_file)
                            print("\nBefore -> After:\nVariables: {} -> {}\nOperators: {} -> {}\n".format(
                                len(sas_task.variables.ranges), len(current.variables.ranges), len(sas_task.operators),
                                len(current.operators)))
                            break

        if self.summary:
            with open("summary.txt", "w") as file:
                for option in trafo_list:  # option is list of removed elements
                    file.write("Removed {}s:\n".format(option[0]))
                    for element in option[1:]:
                        file.write("{}\n".format(str(element)))
                    file.write("\n")

        return sas_file_to_SASTask(new_filename)
