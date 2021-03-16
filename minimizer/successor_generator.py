
from minimizer import visitors
import copy
from minimizer.downward_lib import timers
import random


class SuccessorGenerator():
    def get_successors(self, state):
        pass


class RemoveActions(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        action_names = [action.name for action in task.actions]
        random.Random().shuffle(action_names)
        for name in action_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    visitors.TaskElementEraseActionVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class ReplaceAtomsWithTruth(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    visitors.TaskElementErasePredicateTrueAtomVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class ReplaceAtomsWithFalsity(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    visitors.TaskElementErasePredicateFalseAtomVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class ReplaceLiteralsWithTruth(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    visitors.TaskElementErasePredicateTrueLiteralVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state


class RemoveObjects(SuccessorGenerator):
    def get_successors(self, state):
        task = state["pddl_task"]
        object_names = [obj.name for obj in task.objects]
        random.Random().shuffle(object_names)
        for name in object_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state["pddl_task"]
            with timers.timing("Obtaining successor"):
                child_task = pre_child_task.accept(
                    visitors.TaskElementEraseObjectVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state
