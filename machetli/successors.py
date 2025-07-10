"""
Successor generators in the scope of Machetli are classes with a
:meth:`get_successors(state)<SuccessorGenerator.get_successors>` method defining
how successors of a *state* should be constructed. This module contains the
abstract base class :class:`SuccessorGenerator <SuccessorGenerator>` and some
additional basic functionality. The concrete implementation of a successor
generator depends on the instances it should work on. Some concrete successor
generators for PDDL and SAS\ :sup:`+` files are implemented in the packages
:mod:`machetli.pddl` and :mod:`machetli.sas`. More can be added by
:ref:`extending Machetli<extending-machetli>`.
"""

import random


RNG = random.Random(2024)
"""
Random number generator used for shuffling the order of successors in successor
generators. Using a fixed seed here makes the order of generated successors
reproducible.
"""


class Successor:
    def __init__(self, state, msg):
        self.state = state
        self.change_msg = msg


class SuccessorGenerator:
    """
    Base class for all successor generators.
    """
    def get_successors(self, state):
        """
        Yield successors of *state*.
        """
        raise NotImplementedError
    
    def get_description(self):
        return ""


class ChainingSuccessorGenerator(SuccessorGenerator):
    """
    Executes multiple evaluators in sequences. This successor generator will
    first yield all successors of its first nested generator before yielding
    successors of its second nested generator, and so on. Successors are
    generated on demand, so an expensive-to-compute generator will only generate
    successors that are actually evaluated.

    :param nested_generators: list of other generators that should be chained.
    """
    def __init__(self, nested_generators):
        self.nested_generators = nested_generators
    
    def get_successors(self, state):
        for g in self.nested_generators:
            for s in g.get_successors(state):
                yield s


def make_single_successor_generator(generators):
    """
    :param nested_generators: a single :class:`SuccessorGenerator` or list of
        :class:`SuccessorGenerators<SuccessorGenerator>`".

    :returns: a single :class:`ChainingSuccessorGenerator` chaining all involved
        generators.
    """
    if generators is None:
        return ChainingSuccessorGenerator([])
    elif isinstance(generators, list):
        return ChainingSuccessorGenerator(generators[:])
    elif isinstance(generators, (tuple, set)):
        return ChainingSuccessorGenerator(list(generators))
    else:
        return generators
