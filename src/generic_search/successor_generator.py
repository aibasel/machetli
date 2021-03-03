
from visitor import TaskElementEraseActionVisitor
import copy
from downward_lib import timers
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
            pre_child = copy.deepcopy(task)
            with timers.timing("Obtaining successor"):
                child = pre_child.accept(TaskElementEraseActionVisitor(name))
            yield child
