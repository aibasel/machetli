"""
Machetli evaluators are Python scripts that are started with the path to file
that represents a state in Machetli's search. They check if a certain behavior
occurs for that input and communicate this back to the search with their exit
code. The user documentation contains more information on :ref:`how to write an
evaluator<usage-evaluator>`. This file consolidates how the evaluator functions
are executed.
"""

import logging
from pickle import PickleError
import sys

from machetli.tools import read_state


EXIT_CODE_IMPROVING = 42
"""
Exit code returned by an evaluator if the given state exhibits the behavior
that the evaluator is checking for.
"""
EXIT_CODE_NOT_IMPROVING = 33
"""
Exit code returned by an evaluator if the given state does not exhibit the
behavior that the evaluator is checking for.
"""
EXIT_CODE_RESOURCE_LIMIT = 34
"""
Exit code returned by an evaluator if it ran out of time or memory while
checking the state.
"""
EXIT_CODE_CRITICAL = 35
"""
Exit code returned by an evaluator if a critical error occurred. Any recognized
exit code is also interpreted as a critical error. In particular, 0 is treated
as an error, because it means that the evaluator completed without communicating
a result.
"""


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
    Loads the state passed to the script via its command line arguments, then
    runs the given function `evaluate` and exits the program with the
    appropriate exit code. If the function returns True, `EXIT_CODE_IMPROVING`
    is used, otherwise `EXIT_CODE_NOT_IMPROVING` is used.

    This function is meant to be used as the `main` function, executed in an
    evaluator script. It handles loading the state and can call general
    evaluation functions as well as module-specific ones.

    For testing purposes, scripts with this main function can also be called
    direclty on module-specific inputs (e.g., a domain and problem file for
    the PDDL module).

    :param evaluate: is a function that should return True if the specified
    behavior occurs for the given input, and False if it doesn't. Other ways of
    exiting the function (exceptions, `sys.exit` with exit codes other than
    EXIT_CODE_IMPROVING` or `EXIT_CODE_NOT_IMPROVING`) are treated as failed
    evaluations by the search.
    
    The signature of the function depends on the value of `module`. If no module
    is passed, `evaluate` will be called with the state. If a module was passed,
    that module's `temporary_files` function will be called and the `evaluate`
    function will be called with the names of the resulting files. For example,
    when passing the `pddl` module, the evaluate function is called with the
    names of domain and problem file. See the documentation of the particular
    module for details.

    :param module: is a Python module that will be used to write temporary files
    to disk before calling the evaluation function.
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
