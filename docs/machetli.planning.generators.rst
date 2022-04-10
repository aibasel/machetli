=============================================================
:mod:`machetli.planning.generators` --- Successor Generators
=============================================================

Successor generators in the scope of Machetli are classes with a :meth:`get_successors(state)<machetli.planning.generators.SuccessorGenerator.get_successors>` method defining how successors of a *state* should be constructed. The base class :class:`SuccessorGenerator <machetli.planning.generators.SuccessorGenerator>` has the following form:

.. autoclass:: machetli.planning.generators.SuccessorGenerator
    :members: get_successors

This module provides several implementations of successor generators that can be useful when working with solvers.

Example showcasing the :class:`RemoveActions <machetli.planning.generators.RemoveActions>` successor generator:

    >>> from machetli.planning.generators import RemoveActions
    >>> from machetli.planning.auxiliary import parse_pddl_task
    >>> state = {
    ...     "pddl_task": parse_pddl_task("../examples/issue335_PDDL/cntr-domain.pddl",
    ...     "../examples/issue335_PDDL/cntr-problem.pddl")
    ... }
    >>> # Create a set with all names of the action in the initial state
    >>> initial_actions = {action.name for action in state["pddl_task"].actions}
    >>> len(initial_actions)
    46
    >>> succ_gen = RemoveActions().get_successors(state)
    >>> removed_actions = set()  # Set to track the names of the removed actions
    >>> # Each time, a different action is removed, 
    >>> # which is proven by the increasing size of removed_actions:
    >>> for i in range(3):
    ...     succ = next(succ_gen)
    ...     current_actions = {action.name for action in succ["pddl_task"].actions}
    ...     # Get the removed action via the set difference:
    ...     removed_action = (initial_actions - current_actions)
    ...     removed_actions.update(removed_action)
    ...     print(len(current_actions), len(removed_actions))
    ...
    45 1
    45 2
    45 3
    >>> # Here, the state becomes one action smaller each step:
    >>> for i in range(3):
    ...     succ_gen = RemoveActions().get_successors(state)
    ...     state = next(succ_gen)
    ...     print(len(state["pddl_task"].actions))
    ...
    44
    43
    42


.. automodule:: machetli.planning.generators
    :members: RemoveActions, ReplaceAtomsWithTruth, ReplaceAtomsWithFalsity
    :undoc-members:
    :exclude-members: SuccessorGenerator, transform