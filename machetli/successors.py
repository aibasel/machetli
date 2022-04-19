class Successor:
    def __init__(self, state, msg):
        self.state = state
        self.change_msg = msg


class SuccessorGenerator:
    """Base class for all successor generators.
    """
    def get_successors(self, state):
        """Yield successors of *state*.
        """
        raise NotImplementedError


class ChainingSuccessorGenerator(SuccessorGenerator):
    def __init__(self, nested_generators):
        self.nested_generators = nested_generators
    
    def get_successors(self, state):
        for g in self.nested_generators:
            for s in g.get_successors(state):
                yield s


def make_single_successor_generator(generators):
    if generators is None:
        return ChainingSuccessorGenerator([])
    elif isinstance(generators, list):
        return ChainingSuccessorGenerator(generators[:])
    elif isinstance(generators, (tuple, set)):
        return ChainingSuccessorGenerator(list(generators))
    else:
        return generators
