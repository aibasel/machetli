import argparse
import logging
import os
import platform
import sys

from minimizer import tools
from minimizer.grid import environments, search
from minimizer.grid import slurm_tools as st
from minimizer.search import first_choice_hill_climbing


def get_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", action="store_true")
    parser.add_argument("--evaluate", type=str, metavar="PATH_TO_STATE_DUMP")
    parser.add_argument("--debug", action="store_true")
    return parser


def main(
    initial_state,
    successor_generators,
    evaluator,
    environment=environments.LocalEnvironment(),
):
    """Start a minimizer search and return the resulting state.

    The search is started from *initial_state*, which is a dictionary describing
    the initial conditions of what you want to minimize.
    
    *successor_generators* is
    a single class name or a list of multiple ones whose implementation define(s)
    how successors of a state are generated. When a list is given, the search is
    performed serially with each of them, starting from the resulting state of the
    search with the preceding successor generator. Successor generators must
    implement the
    :class:`SuccessorGenerator <minimizer.planning.generators.SuccessorGenerator>`
    class.

    *evaluator* is the name of the class that was implemented to evaluate a state
    during the search. Evaluator implementations must be derived from the
    :class:`Evaluator <minimizer.evaluator.Evaluator>` class.

    *environment* determines whether the search should be done on a local machine
    or on a Slurm computing grid. Use :class:`minimizer.grid.environments.LocalEnvironment`
    or an implementation of :class:`minimizer.grid.environments.SlurmEnvironment`.

    When performing the search on a Slurm grid, the possibility of failure at some
    point is increased due to the introduced parallelism on multiple nodes and an
    I/O load over the network filesystem. When setting *enforce_order* to ``True``,
    the :func:`search <minimizer.grid.search.search>` function will enforce that
    the search is aborted if a single task fails and no successor from an earlier
    task is accepted.

    *batch-size* regulates how many successors at most are evaluated in parallel,
    when executing the search on the grid.

    Example of the main function in action:

    .. literalinclude:: ../examples/issue335_PDDL/local_test.py
        :language: python
        :caption:
        :lines: 60-72
        :emphasize-lines: 10-13
    """

    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    tools.configure_logging() if not args.debug else tools.configure_logging(
        level=logging.DEBUG)

    if args.evaluate:
        dump_file_path = args.evaluate
        for _ in range(10):
            _random_sleep()
            if os.path.exists(dump_file_path):
                break
        else:
            sys.exit(1)  # Make evaluation fail if state file is not found after 10 attempts.
        state = st.read_and_unpickle_state(dump_file_path)
        state["cwd"] = os.path.dirname(dump_file_path)
        result = evaluator().evaluate(state)
        logging.info(f"Node: {platform.node()}")
        sys.exit(0) if result else sys.exit(1)

    elif isinstance(environment, environments.LocalEnvironment):
        return first_choice_hill_climbing(initial_state=initial_state,
                                          successor_generators=successor_generators,
                                          evaluator=evaluator)

    elif isinstance(environment, environments.SlurmEnvironment):
        result = search.search_grid(initial_state=initial_state,
                                    successor_generators=successor_generators,
                                    environment=environment,
                                    enforce_order=environment.enforce_order,
                                    batch_size=environment.batch_size)
        st.launch_email_job(environment)
        return result
    else:
        arg_parser.print_usage()


def _random_sleep():
    """Sleep for 1-5 seconds, chosen at random."""
    import random
    import time
    time.sleep(random.randint(1, 5))
