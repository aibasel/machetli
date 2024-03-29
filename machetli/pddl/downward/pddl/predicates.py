from machetli.pddl.downward.pddl.task_element import TaskElement


class Predicate(TaskElement):

    def accept(self, visitor):
        return visitor.visit_predicate(self)

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def __str__(self):
        return "%s(%s)" % (self.name, ", ".join(map(str, self.arguments)))

    def get_arity(self):
        return len(self.arguments)
