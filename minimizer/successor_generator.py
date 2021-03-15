
from minimizer.visitor import TaskElementEraseActionVisitor
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
                child_task = pre_child_task.accept(TaskElementEraseActionVisitor(name))
            child_state["pddl_task"] = child_task
            yield child_state
