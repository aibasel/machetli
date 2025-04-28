#!/usr/bin/env python

import argparse

from machetli import pddl
from machetli.evaluator import is_evaluator_successful

parser = argparse.ArgumentParser()
parser.add_argument("evaluator_path", type=str)
parser.add_argument("domain", type=str)
parser.add_argument("problem", type=str)
args = parser.parse_args()

initial_state = pddl.generate_initial_state(args.domain, args.problem)

print("Testing evaluator...")
if is_evaluator_successful(args.evaluator_path, initial_state):
    print("Success: evaluator finds bug in initial state!")
else:
    print("Fail: evaluator doesn't find bug in initial state.")

