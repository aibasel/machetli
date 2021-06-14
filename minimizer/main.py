import argparse
import logging
import os
import platform
import sys

from lab import tools
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
    enforce_order=False,
    batch_size=st.DEFAULT_ARRAY_SIZE
):

    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    tools.configure_logging() if not args.debug else tools.configure_logging(
        level=logging.DEBUG)

    if args.evaluate:
        dump_file_path = args.evaluate
        if not environment.wait_for_filesystem(dump_file_path): sys.exit(1)
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
                                       enforce_order=enforce_order,
                                       batch_size=batch_size)
        st.launch_email_job(environment)
        return result
    else:
        arg_parser.print_usage()
