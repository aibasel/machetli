import copy
import logging
import random

from machetli.pddl import visitors
from machetli.pddl.constants import KEY_IN_STATE
from machetli.successors import Successor, SuccessorGenerator


class RemoveActions(SuccessorGenerator):
    """
    Successor generator that removes actions from the PDDL task in a
    state. Actions are removed in a random order.
    """
    def get_successors(self, state):
        """
        Yield modified versions of *state* of which in each one a different
        action is removed from the PDDL task stored in ``state[KEY_IN_STATE]``.
        """
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
    """Successor generator that removes predicates from the PDDL task in
    a state. This is accomplished by scanning the entire task for the
    atom to be removed, instantiating each instance of this atom with a
    constant according to *replace_with*:

    * ``"true"`` replaces all atoms of the removed predicate with true,
    * ``"false"`` replaces all atoms of the removed predicate with false, and
    * ``"dynamic"`` (default) replaces an atom of the removed predicate with
      true if it occurs positively and with false otherwise.

    Predicates are removed in a random order.
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
    Successor generator that removes objects from the PDDL task in a
    state. Objects are removed in a random order.
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
