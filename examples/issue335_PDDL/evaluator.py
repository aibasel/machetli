import os
import sys

from minimizer.parser import Parser
from minimizer.planning import auxiliary
from minimizer.run import Run, run_and_parse_all


# The Fast Downward issue we use for this example is from 2014. The code of the
# planner from that time is only compatible with Python versions < 3.8.
try:
    PYTHON37 = os.environ["PYTHON_3_7"]
    PLANNER_REPO = os.environ["DOWNWARD_REPO"]
except KeyError:
    msg = """
Make sure to set the environment variables PYTHON_3_7 and DOWNWARD_REPO.
PYTHON_3_7:     Path to Python 3.7 executable (due to older Fast Downward version).
DOWNWARD_REPO:  Path to Fast Downward repository (https://github.com/aibasel/downward)
                at commit 09ccef5fd.
    """
    sys.exit(msg)

# The bug we want to isolate occurs in the translate module, so we define
# a shortcut to it.
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")


# The evaluation function we are defining here will later be used
# in the search function. It will be executed during the search to
# check if generated states still produce the behaviour we are searching for.
def evaluate(state):
    # The following context manager generates temporary PDDL files for
    # the pddl task stored in *state* so they can be used in the execution
    # of the run.
    with auxiliary.state_with_generated_pddl_files(state) as local_state:
        command = [
            PYTHON37,
            TRANSLATOR,
            ## TODO: return filenames in context manager instead of modified state
            f"{local_state['generated_pddl_domain_filename']}",
            f"{local_state['generated_pddl_problem_filename']}"]

        run = Run(command, time_limit=20, memory_limit=3338)

        ## TODO: add functionality to store logs {always, only on error} to the Run class. See run.py run_all.
        stdout, stderr, returncode = run.start(state)

        ## TODO: add parsing methods?
        return "AssertionError: Negated axiom impossible" in stderr



