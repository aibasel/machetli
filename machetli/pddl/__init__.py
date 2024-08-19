"""
This package allows transforming PDDL input files. Usually, in a
Machetli script you will use it in the following way:

.. code-block:: python

    from machetli import pddl
    initial_state = pddl.generate_initial_state("path/to/domain.pddl", "path/to/problem.pddl")
    successor_generators = [pddl.RemoveActions(), ...]

You can then start your Machetli search using the initial PDDL problem
``initial_state`` and a set of PDDL successor generators
``successor_generators``. Finally, write out your results using

.. code-block:: python

    pddl.write_files(result, "path/to/result-domain.pddl", "path/to/result-problem.pddl")

where ``result`` is the value returned by the
:meth:`search<machetli.search>` function.

The successor generators described below denote possible transformations.
"""

from machetli.pddl.files import generate_initial_state, temporary_files, \
    write_files, run_evaluator

# We specify the imported functions and classes in __all__ so they will be
# documented when the documentation of this package is generated.
__all__ = ["generate_initial_state", "temporary_files", "write_files", "run_evaluator"]


def _import_successor_generators():
    # Import all successor generators and put them in the package namespace
    # so users can access them without knowing about the subpackage generators.
    import machetli.pddl.generators as generators

    for key, value in generators.__dict__.items():
        if (isinstance(value, type)
            and issubclass(value, generators.SuccessorGenerator)
                and value != generators.SuccessorGenerator):
            __all__.append(key)
            globals()[key] = value


_import_successor_generators()
del _import_successor_generators
