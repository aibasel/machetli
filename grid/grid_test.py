#! /usr/bin/env python

from lab import tools
import sys
import os
script_path = tools.get_script_path()
script_dir = os.path.dirname(script_path)
minimizer_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.append(minimizer_dir)

from minimizer.grid import slurm_tools
import time
import random
import argparse

def successors(state):
    print(f"expanding {state}")
    if state["level"] > 4:
        return
    for i in range(4):
        succ = dict(state)
        succ["level"] = state["level"] + 1
        succ["id"] = i
        yield succ


def evaluate(state):
    print(f"evaluating {state}")
    time.sleep(random.randint(1, 6)) # seconds
    return state["level"] <= 3 and state["id"] == 2


def create_initial_state():
    return {"level": 1, "id": 3}


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

print(search_local())

def search_grid():
    state = create_initial_state()
    batch_num = 0
    while True:
        batch_num += 1
        successor_generator = successors(state)
        batch_of_successors = slurm_tools.get_next_batch(successor_generator, batch_num)
        if not batch_of_successors:
            break

        job_id = slurm_tools.submit_array_job(batch_of_successors)
        wait_for_grid(job_id)
        for succ in batch_of_successors:
            result = get_result(succ)
            if result:
                state = succ
                break
    return state


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", action="store_true")
    parser.add_argument("--evaluate", type=str)
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)


if __name__ == "__main__":
    main()


#run_search()
# ./grid_test.py --> search_local
# ./grid_test.py --grid --> search_grid
# ./grid_test.py --evaluate directory_14 --> evaluate(load(directory_14/state))
