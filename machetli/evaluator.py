"""
TODO issue82: rewrite this (and find a new place for it?)

Machetli evaluators are Python files that define a function
:meth:`evaluate(state)<>`. This function takes the current state of the search
and should check if the behavior you are looking for still is present. The user
documentation contains more information on :ref:`how to write an
evaluator<usage-evaluator>`.

This module provides a function to import and and run the evaluator given the
filename. It can also be called from the command line for a pickled state:

.. code-block:: bash

    python -m machetli.evaluator /path/to/evaluator.py /path/to/state.pickle

This is used when executing Machetli on the grid. The call will exit with an
exit code of 42 if the evaluator reports the state as improving, and an exit
code of 33 if the state is non-improving. All other exit codes are treated as
errors in the search.
"""

import logging
from pickle import PickleError
import sys

from machetli.tools import read_state


EXIT_CODE_IMPROVING = 42
EXIT_CODE_NOT_IMPROVING = 33
EXIT_CODE_RESOURCE_LIMIT = 34
EXIT_CODE_CRITICAL = 35


def _get_state_from_filenames(module, filenames):
    """
    Attempts to read a state from the file(s) in *filenames*. A single filename
    is first interpreted as a pickled state. If unpickling the state doesn't
    work or a different number of filenames are given, control is handed off to
    a method *generate_initial_state* in *module* if it exists.
    """

    if len(filenames) == 1:
        try:
            return read_state(filenames[0])
        except (FileNotFoundError, PickleError):
            pass

    try:
        return module.generate_initial_state(*filenames)
    except (AttributeError, TypeError, FileNotFoundError):
        logging.critical(f"Could not load or create a state from files {filenames}")
        sys.exit(EXIT_CODE_CRITICAL)


def main(evaluate, module=None):
    #TODO issue82: doc string
    state = _get_state_from_filenames(module, sys.argv[1:])

    if module:
        with module.temporary_files(state) as tmp_filenames:
            improving = evaluate(*tmp_filenames)
    else:
        improving = evaluate(state)

    if improving:
        sys.exit(EXIT_CODE_IMPROVING)
    else:
        sys.exit(EXIT_CODE_NOT_IMPROVING)
