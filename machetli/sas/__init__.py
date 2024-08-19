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
from machetli.sas.files import generate_initial_state, temporary_file, \
    write_file, run_evaluator

# We specify the imported functions and classes in __all__ so they will be
# documented when the documentation of this package is generated.
__all__ = ["generate_initial_state", "temporary_file", "write_file",
           "run_evaluator"]


def _import_successor_generators():
    # Import all successor generators and put them in the package namespace
    # so users can access them without knowing about the subpackage generators.
    import machetli.sas.generators as generators

    for key, value in generators.__dict__.items():
        if (isinstance(value, type)
            and issubclass(value, generators.SuccessorGenerator)
                and value != generators.SuccessorGenerator):
            __all__.append(key)
            globals()[key] = value


_import_successor_generators()
del _import_successor_generators
