"""
Machetli evaluators are Python functions that take a list of files as
input and check if a certain behavior occurs for that input. The user
documentation contains more information on :ref:`how to write an
evaluator<usage-evaluator>`. This file consolidates how the evaluator
functions are executed.
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
    """
    Runs the evaluator function given a specific input. It exits
    with an exit code of 42 if the evaluator reports that the specified
    behavior occurs for the given input, and an exit code of 33 if it does
    not occur for this input. All other exit codes are treated as errors in
    the search.
    """
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
