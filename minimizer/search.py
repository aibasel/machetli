from minimizer.downward_lib import timers
from minimizer.sas_reader import sas_file_to_SASTask
from minimizer.pddl_writer import write_PDDL
from minimizer.state import update_task, update_PDDL_call_strings, update_SAS_call_strings
import copy
import subprocess
import os
import sys


def first_choice_hill_climbing(initial_state, successor_generators, evaluator):
    if not isinstance(successor_generators, list):
        successor_generators = [successor_generators]
    # is_pddl_task = False
    # if "pddl_task" in initial_state:
    #     is_pddl_task = True
    # original_task = initial_state[
    #     "pddl_task"] if is_pddl_task else initial_state["sas_task"]
    # write_PDDL(original_task, NEW_DOMAIN_FILENAME, NEW_PROBLEM_FILENAME)
    current_state = initial_state
    # current_state = update_PDDL_call_strings(
    #     current_state, NEW_DOMAIN_FILENAME, NEW_PROBLEM_FILENAME) if is_pddl_task else update_SAS_call_strings(current_state, NEW_SAS_FILENAME)

    with timers.timing("Starting first-choice hill-climbing search"):
        for succ_gen in successor_generators:
            print()
            with timers.timing("Generating successors with class {}".format(
                    succ_gen.__name__)):
                # current_task = current_state[
                #     "pddl_task"] if is_pddl_task else current_state["sas_task"]
                num_children = 0
                num_successors = 0
                print()
                while True:
                    if num_children > 0:
                        print(
                            "Child found ({}), evaluated {} successor{}.\n"
                            .format(num_children, num_successors, "s" if num_successors > 1 else ""))
                    num_successors = 0
                    num_children += 1
                    # for successor_task, removed_element in succ_gen().get_successors(current_state):
                    for successor_state in succ_gen().get_successors(current_state):
                        num_successors += 1
                        # write_PDDL(successor_task, NEW_DOMAIN_FILENAME,
                        #            NEW_PROBLEM_FILENAME)
                        # current_state = update_task(current_state,
                        #                             successor_task)
                        if evaluator().evaluate(current_state):
                            # current_task = successor_task
                            current_state = successor_state
                            break  # successor selected by first choice
                    else:
                        print(
                            "No successor found by evaluator, end of first-choice hill-climbing."
                        )
                        # if is_pddl_task:
                        #     write_PDDL(current_task, NEW_DOMAIN_FILENAME,
                        #                NEW_PROBLEM_FILENAME)
                        #     original_task.predicates = [
                        #         pred for pred in original_task.predicates
                        #         if not pred.name == "="
                        #     ]
                        #     current_task.predicates = [
                        #         pred for pred in current_task.predicates
                        #         if not pred.name == "="
                        #     ]
                        break
