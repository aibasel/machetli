import copy
import logging
import random

from machetli.pddl import visitors
from machetli.pddl.constants import KEY_IN_STATE
from machetli.successors import Successor, SuccessorGenerator


class RemoveActions(SuccessorGenerator):
    """
    For each action schema in the PDDL domain, generate a successor
    where this action schema is removed. The order of the successors is
    randomized.
    """
    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        action_names = [action.name for action in task.actions]
        random.Random().shuffle(action_names)
        for name in action_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = pre_child_task.accept(
                visitors.TaskElementEraseActionVisitor(name))
            yield Successor(child_state,
                            f"Removed action '{name}'. Remaining actions: {len(task.actions) - 1}")


class RemovePredicates(SuccessorGenerator):
    """
    For each predicate in the PDDL domain, generate a successor where
    this predicate is compiled away. This is accomplished by scanning
    the entire task for the atom to be removed, instantiating each
    instance of this atom with a constant according to ``replace_with``:

    * ``"true"`` replaces all atoms of the removed predicate with true,
    * ``"false"`` replaces all atoms of the removed predicate with false, and
    * ``"dynamic"`` (default) replaces an atom of the removed predicate with
      true if it occurs positively and with false otherwise.

    The order of the successors is randomized.
    """
    def __init__(self, replace_with="dynamic"):
        self.replace_with = replace_with
        if replace_with == "dynamic":
            self.visitor = visitors.TaskElementErasePredicateTrueLiteralVisitor
        elif replace_with == "true":
            self.visitor = visitors.TaskElementErasePredicateTrueAtomVisitor
        elif replace_with == "false":
            self.visitor = visitors.TaskElementErasePredicateFalseAtomVisitor
        else:
            logging.critical(f"Used unknown option '{replace_with}' for "
                             f"replacing predicates.")

    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        predicate_names = [predicate.name for predicate in task.predicates if
                           not (predicate.name == "dummy_axiom_trigger" or predicate.name == "=")]
        random.Random().shuffle(predicate_names)
        for name in predicate_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = pre_child_task.accept(self.visitor(name))
            yield Successor(
                child_state,
                f"Removed predicate '{name}'. Remaining predicates: {len(task.predicates) - 1}")


class RemoveObjects(SuccessorGenerator):
    """
    For each object in the PDDL problem, generate a successor that
    removes this object from the PDDL task. The order of the successors
    is randomized.
    """
    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        object_names = [obj.name for obj in task.objects]
        random.Random().shuffle(object_names)
        for name in object_names:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = pre_child_task.accept(
                visitors.TaskElementEraseObjectVisitor(name))
            yield Successor(child_state,
                            f"Removed object '{name}'. Remaining objects: {len(task.objects) - 1}")

class RemoveInit(SuccessorGenerator):
    """
    For each fact in the initial state of the PDDL problem, generate a successor
    where this fact is removed from init. The order of the successors is randomized.
    """
    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        init_facts = task.init
        random.Random().shuffle(init_facts)
        for fact in init_facts:
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = pre_child_task.accept(
                TaskElementEraseInitFactVisitor(fact))
            yield Successor(child_state,
                            f"Removed fact '{fact}' from init. Remaining facts: {len(task.init) - 1}")

class RemoveGoal(SuccessorGenerator):
    """
    For each literal in the goal of the PDDL problem, generate a successor
    where this literal is replaced by true in the goal.
    The order of the successors is randomized.
    """
    def get_successors(self, state):
        task = state[KEY_IN_STATE]
        goal_literals = GetLiteralsVisitor().visit_condition(task.goal)
        random.Random().shuffle(goal_literals)
        for fact in goal_literals:
            print(fact)
            child_state = copy.deepcopy(state)
            pre_child_task = child_state[KEY_IN_STATE]
            child_state[KEY_IN_STATE] = pre_child_task.accept(TaskElementEraseGoalLiteralVisitor(fact))
            yield Successor(child_state,f"Removed fact '{fact}' from goal. Remaining facts: {len(goal_literals) - 1}")



