
from minimizer.downward_lib import pddl_parser
import os
import sys
dirname = os.path.dirname(__file__)
downward_lib = os.path.join(dirname, "downward_lib/")
sys.path.append(downward_lib)


def read_PDDL_task(dom_filename, prob_filename):
    return pddl_parser.open(domain_filename=dom_filename,
                            task_filename=prob_filename)


def read_SAS_task(task_filename):
    return sas_file_to_SASTask(task_filename)


def update_task(state, task):
    assert "pddl_task" in state or "sas_task" in state
    if "pddl_task" in state:
        state["pddl_task"] = task
    elif "sas_task" in state:
        state["sas_task"] = task
    return state


def update_PDDL_call_strings(state, dom_filename, prob_filename):
    for cmd in state["call_strings"]:
        positions = []
        for pos, arg in enumerate(cmd):
            if ".pddl" in arg:
                positions.append(pos)
        assert len(positions) == 2
        dom_position = positions[0]
        prob_position = positions[1]
        state["call_strings"][cmd][dom_position] = dom_filename
        state["call_strings"][cmd][prob_position] = prob_filename
    return state


def update_SAS_call_strings(state, sas_filename):
    for cmd in state["call_strings"]:
        for pos, arg in enumerate(cmd):
            if ".sas" in arg:
                state["call_strings"][cmd][pos] = sas_filename
                break
    return state
