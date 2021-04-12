#! /usr/bin/env python

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

# print(search_local())

# def search_grid():
#     state = create_initial_state()
#     while True:
#         successor_generator = successors(state)
#         batch_of_successors = get_next_batch(successor_generator)
#         if no more successors:
#             break

#         job_id = submit_batch(batch_of_successors)
#         wait_for_grid(job_id)
#         for succ in batch_of_successors:
#             result = get_result(succ)
#             if result:
#                 state = succ
#                 break
#     return state


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
