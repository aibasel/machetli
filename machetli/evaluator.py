"""
Machetli evaluators are Python scripts that are started with the path to file
that represents a state in Machetli's search. They check if a certain behavior
occurs for that input and communicate this back to the search with their exit
code. The user documentation contains more information on :ref:`how to write an
evaluator<usage-evaluator>`. This file defines the exit codes and offers a
general convenience function for implementing evaluators. Additional convenience
functions come with specific modules.
"""

import logging
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


def run_evaluator(evaluate):
    """
    Loads the state passed to the script via its only command line argument,
    then runs the given function `evaluate` and exits the program with the
    appropriate exit code. If the function returns True, `EXIT_CODE_IMPROVING`
    is used, otherwise `EXIT_CODE_NOT_IMPROVING` is used.

    This function is meant to be used as the `main` function of an evaluator
    script. Module-specific overloads are available in the modules for more
    convenient evaluation functions and for testing the evaluator.

    :param evaluate: is a function taking a state and returning True if the
    specified behavior occurs for the given input, and False if it doesn't.
    Other ways of exiting the function (exceptions, `sys.exit` with exit codes
    other than EXIT_CODE_IMPROVING` or `EXIT_CODE_NOT_IMPROVING`) are treated as
    failed evaluations by the search.
    """
    if len(sys.argv) != 2:
        logging.critical("Expected path to the state to evaluate as the single command line parameter.")
        sys.exit(EXIT_CODE_CRITICAL)
    state = read_state(sys.argv[1])

    if evaluate(state):
        sys.exit(EXIT_CODE_IMPROVING)
    else:
        sys.exit(EXIT_CODE_NOT_IMPROVING)
