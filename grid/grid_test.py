#! /usr/bin/env python

import argparse
import random
import time
from lab import tools
import sys
import os
script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)
minimizer_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.append(minimizer_dir)
from minimizer.grid import slurm_tools
from minimizer.minimizer.run import Run
import logging


def successors(state):
    logging.debug(f"Python interpreter: {tools.get_python_executable()}")
    print(f"expanding {state}")
    if state["level"] > 4:
        return
    for i in range(10):
        succ = dict(state)
        succ["level"] = state["level"] + 1
        succ["id"] = i
        yield succ


def evaluate(state):
    print(f"evaluating {state}")
    time.sleep(2)  # seconds
    return state["level"] <= 3 and state["id"] == 8


def create_initial_state():
    return {"level": 1, "id": 3, "runs": [Run(["echo", "hello"], time_limit=60)]}


def search_local():
    state = create_initial_state()
    while True:
        for succ in successors(state):
            if evaluate(succ):
                state = succ
                break
        else:
            break
    return state


def search_grid():
    env = slurm_tools.MinimizerSlurmEnvironment()
    state = create_initial_state()
    batch_num = 0
    while True:
        successor_generator = successors(state)
        batch_of_successors = slurm_tools.get_next_batch(successor_generator)
        if not batch_of_successors:
            break
        dump_dirs = env.submit_array_job(batch_of_successors, batch_num)

        assert len(batch_of_successors) == len(
            dump_dirs), "Something went wrong, batch size and number of dump directories should be the same."
        for succ, dump_dir in zip(batch_of_successors, dump_dirs):
            dump_path = os.path.join(dump_dir, slurm_tools.DUMP_FILENAME)
            try:
                result = slurm_tools.get_result(dump_path)
            except KeyError as kerr:
                err_message = None
                err_logfile = os.path.join(dump_dir, "driver.err")
                if os.path.exists(err_logfile):
                    with open(err_logfile, "r") as file:
                        err_message = file.read()
                err_info = f"\nError message:\n{err_message}" if err_message else ""
                truncated_dir = os.path.join(*dump_dir.split(os.sep)[-2:])
                print(f"Evaluation result for state in {truncated_dir} not present.\n{err_info}")
                result = False
            if result:
                state = succ
                break
        else:
            break
        batch_num += 1
    return state


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", action="store_true")
    parser.add_argument("--evaluate", type=str)
    return parser.parse_args()


def main():
    tools.configure_logging()
    args = parse_args()
    if args.evaluate:
        logging.debug(f"Python interpreter: {tools.get_python_executable()}")
        dump_file_path = args.evaluate
        state = slurm_tools.read_and_unpickle_state(dump_file_path)
        result = evaluate(state)
        slurm_tools.add_result_to_state(result, dump_file_path)
    elif args.grid:
        print(search_grid())
    else:
        print(search_local())


if __name__ == "__main__":
    main()


# run_search()
# ./grid_test.py --> search_local
# ./grid_test.py --grid --> search_grid
# ./grid_test.py --evaluate directory_14 --> evaluate(load(directory_14/state))
