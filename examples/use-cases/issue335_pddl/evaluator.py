import os

from machetli import pddl, tools

PYTHON37 = os.environ["PYTHON_3_7"]
PLANNER_REPO = os.environ["DOWNWARD_REPO"]
TRANSLATOR = os.path.join(PLANNER_REPO, "src/translate/translate.py")

# The evaluation function we are defining here is used in the search function.
# It is executed during the search to check if generated states still produce
# the behaviour we are searching for.
def evaluate(state):
    # The following context manager temporarily write the task stored in *state*
    # to files that are automatically deleted afterwards.
    with pddl.temporary_files(state) as (domain_filename, problem_filename):
        command = [PYTHON37, TRANSLATOR, f"{domain_filename}", f"{problem_filename}"]
        run = tools.Run(command, time_limit=20, memory_limit=3338)

        ## TODO: add functionality to store logs {always, only on error} to the Run class. See run.py run_all.
        stdout, stderr, returncode = run.start()

        ## TODO: add parsing methods?
        return "AssertionError: Negated axiom impossible" in stderr
