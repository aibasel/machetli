"""
Machetli evaluators are Python scripts that are started with the path to a file
that represents a state in Machetli's search. They check if a certain behavior
occurs for that input and communicate this back to the search with their exit
code. The user documentation contains more information on :ref:`how to write an
evaluator<usage-evaluator>`. This file defines the exit codes and offers a
general convenience function for implementing evaluators. Additional convenience
functions come with specific packages.
"""

import logging
import sys

from machetli.tools import read_state


EXIT_CODE_BEHAVIOR_PRESENT = 42
"""
Exit code returned by an evaluator if the given state exhibits the behavior
that the evaluator is checking for.
"""
EXIT_CODE_BEHAVIOR_NOT_PRESENT = 33
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
    Load the state passed to the script via its only command line arguments,
    then run the given function *evaluate* on it, and exit the program with the
    appropriate exit code. If the function returns ``True``, use
    :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>`,
    otherwise use
    :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_NOT_PRESENT>`.

    This function is meant to be used as the main function of an evaluator
    script. Package-specific overloads are available for more convenient
    evaluation functions and for testing the evaluator.

    :param evaluate: is a function taking the filename of a state as
        input and returning ``True`` if the specified behavior occurs for the
        given instance, and ``False`` if it doesn't. Other ways of exiting the
        function (exceptions, ``sys.exit`` with exit codes other than
        :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>` or
        :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_NOT_PRESENT>`)
        are treated as failed evaluations by the search.

    """
    if len(sys.argv) != 2:
        logging.critical("Expected path to the state to evaluate as the single "
                         "command line parameter.")
        sys.exit(EXIT_CODE_CRITICAL)
    state = read_state(sys.argv[1])

    if evaluate(state):
        sys.exit(EXIT_CODE_BEHAVIOR_PRESENT)
    else:
        sys.exit(EXIT_CODE_BEHAVIOR_NOT_PRESENT)
