import os

from minimizer.planning import auxiliary
from minimizer.run import Run

PYTHON37 = os.environ["PYTHON_3_7"]
PLANNER_REPO = os.environ["DOWNWARD_REPO"]
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")

# The evaluation function we are defining here is used in the search function.
# It is executed during the search to check if generated states still produce
# the behaviour we are searching for.
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
