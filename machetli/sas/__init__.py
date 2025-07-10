"""
This package allows transforming SAS\ :sup:`+` input files. Usually, in
a Machetli script you will use it in the following way:

.. code-block:: python

    from machetli import sas
    initial_state = sas.generate_initial_state("path/to/problem.sas")
    successor_generators = [sas.RemoveOperators(), ...]

You can then start your Machetli search using the initial SAS\ :sup:`+`
problem ``initial_state`` and a set of SAS\ :sup:`+` successor
generators ``successor_generators``. Finally, write out your result
using

.. code-block:: python

    sas.write_files(result, "path/to/result-problem.sas")

where ``result`` is the value returned by the
:meth:`search<machetli.search>` function.

The successor generators described below denote possible transformations.
"""
from machetli.sas.files import generate_initial_state, write_file, run_evaluator

# We specify the imported functions and classes in __all__ so they will be
# documented when the documentation of this package is generated.
__all__ = ["generate_initial_state", "write_file", "run_evaluator"]


def _get_successor_generators():
    # Import all successor generators and return a dict mapping names to classes.
    import machetli.sas.generators as generators
    all_generators = {}

    for key, value in generators.__dict__.items():
        if (isinstance(value, type)
            and issubclass(value, generators.SuccessorGenerator)
                and value != generators.SuccessorGenerator):
            all_generators[key] = value
    return all_generators

def _add_to_package_namespace(generators):
    # Plance generators in the package namespace so users can access them without
    # knowing about the subpackage generators.
    for key, value in generators.items():
        __all__.append(key)
        globals()[key] = value

GENERATORS = _get_successor_generators()
_add_to_package_namespace(GENERATORS)

del _get_successor_generators
del _add_to_package_namespace