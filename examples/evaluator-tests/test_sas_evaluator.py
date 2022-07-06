#!/usr/bin/env python

import argparse

from machetli import sas, tools
from machetli.evaluator import is_evaluator_successful

parser = argparse.ArgumentParser()
parser.add_argument("evaluator_path", type=str)
parser.add_argument("problem", type=str)
args = parser.parse_args()

original_problem = sas.generate_initial_state(args.problem)

print("Testing evaluator...")
if is_evaluator_successful(args.evaluator_path, original_problem):
    print("Success: evaluator finds bug in original problme!")
else:
    print("Fail: evaluator doesn't find bug in original problem.")

