"""
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

import importlib.util
import logging
import platform
import sys

from machetli.tools import read_state

EXIT_CODE_IMPROVING = 42
EXIT_CODE_NOT_IMPROVING = 33
EXIT_CODE_RESOURCE_LIMIT = 34

# https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path/50395128#50395128
def _import_evaluator(module_name, evaluator_path):
    spec = importlib.util.spec_from_file_location(module_name, evaluator_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module 
    spec.loader.exec_module(module)
    return module


def is_evaluator_successful(evaluator_path, state):
    """
    Import the Python module specified in *evaluator_path* and run its
    :meth:`evaluate` function on *state*. Return the return value of
    :meth:`evaluate`. See the user documentation on :ref:`how to write an
    evaluator<usage-evaluator>`.
    """
    module = _import_evaluator("custom_evaluator", evaluator_path)
    return module.evaluate(state)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.critical(f"Expected two arguments to machetli.evaluator but got {len(sys.argv)}.")
    evaluator_path = sys.argv[1]
    state_filename = sys.argv[2]
    logging.info(f"Running evaluator '{evaluator_path}' for state '{state_filename}' on node: {platform.node()}.")

    state = read_state(state_filename, 5, 2)
    if is_evaluator_successful(evaluator_path, state):
        sys.exit(EXIT_CODE_IMPROVING)
    else:
        sys.exit(EXIT_CODE_NOT_IMPROVING)
