#!/usr/bin/env python3

import argparse
import random
import time
import sys
import os

from lab import tools
from grid import slurm_tools
from minimizer.run import Run
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


def search_grid(enforce_order=False):
    env = slurm_tools.MinimizerSlurmEnvironment()
    state = create_initial_state()
    batch_num = 0
    while True:
        successor_generator = successors(state)
        batch_of_successors = slurm_tools.get_next_batch(successor_generator)
        if not batch_of_successors:
            break
        try:
            job_id, run_dirs = env.submit_array_job(
                batch_of_successors, batch_num)
            env.poll_job(job_id, batch_of_successors)
        except slurm_tools.SubmissionError as e:
            if not enforce_order:
                logging.warning(
                    f"The following batch submission failed but is ignored:\n{e}")
            else:
                logging.critical(
                    f"Order cannot be kept because the following batch submission failed:\n{e}")
        except slurm_tools.TaskError as e:
            indices_critical_tasks = [parts[1] for parts in (
                job_id.split("_") for job_id in e.critical_tasks)]
            if not enforce_order:
                # remove successors and their directories if their task entered a critical state
                for task_index in indices_critical_tasks:
                    del batch_of_successors[task_index]
                    del run_dirs[task_index]
                logging.warning(
                    f"At least one task from job {job_id} entered a critical state but is ignored:\n{e}")
            else:
                # since order needs to be enforced, only consider successors before first successor with failed task
                first_failed_index = indices_critical_tasks[0]
                batch_of_successors = batch_of_successors[:first_failed_index]
                run_dirs = run_dirs[:first_failed_index]
                if first_failed_index == 0:  # the task of the first successor entered a critical state
                    logging.critical(
                        f"At least the first task from job {job_id} entered a critical state and the search is aborted.\n{e}")
                else:
                    logging.warning(f"""At least one task from job {job_id} entered a critical state.
                    The successors before the first one whose task entered the critical state are still considered.\n{e}""")

        for succ, run_dir in zip(batch_of_successors, run_dirs):
            driver_err_file = os.path.join(run_dir, slurm_tools.DRIVER_ERR)
            if os.path.exists(driver_err_file):
                if enforce_order:
                    logging.warning(f"Evaluation failed for state in {run_dir}. No further successor is considered.")
                    break
                else:
                    logging.warning(f"Evaluation failed for state in {run_dir}. Continuing search.")
                    result = False
            else:
                dump_file = os.path.join(run_dir, slurm_tools.DUMP_FILENAME)
                result = slurm_tools.get_result(dump_file)
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
