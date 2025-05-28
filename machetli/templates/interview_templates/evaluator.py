#!/usr/bin/env python3

import os

from machetli import pddl, tools

def evaluate(domain, problem):
    command = "{COMMAND_AS_LIST}"
    result = tools.run(command, cpu_time_limit=10,
                       memory_limit=3000, text=True)

    return "{STRING_IN_OUTPUT}" in result.stdout

if __name__ == "__main__":
    pddl.run_evaluator(evaluate)
