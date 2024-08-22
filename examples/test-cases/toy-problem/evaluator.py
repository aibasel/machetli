#!/usr/bin/env python3

import logging
from machetli import tools, evaluator


def evaluate(state):
    """
    Expected search behavior:
    Expanding: <0,0>
      Evaluating: <0,1>
      Evaluating: <1,1>
      Evaluating: <2,1>
    Expanding: <2,1>
      Evaluating: <0,2>
      Evaluating: <1,2>
    Expanding: <1,2>
      Evaluating: <0,3>
    Expanding: <0,3>
      Evaluating: <0,4>
      Evaluating: <1,4>
      Evaluating: <2,4>
      Evaluating: <3,4>
      Evaluating: <4,4>
    Search Result: <0,3>
    """
    state_id = state["id"]
    level = state["level"]
    # TODO: This was previously displayed on stdout locally but is not anymore.
    logging.info(f"Evaluating: <id={state_id}, level={level}>")

    tools.run_with_limits(["echo", "Hello", "world"])
    return level + state_id == 3


if __name__ == "__main__":
    evaluator.run_evaluator(evaluate)
