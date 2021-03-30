from minimizer.sas_reader import sas_file_to_SASTask
from minimizer.downward_lib import pddl_parser

NEW_DOMAIN_FILENAME = "minimized-domain.pddl"
NEW_PROBLEM_FILENAME = "minimized-problem.pddl"
NEW_SAS_FILENAME = "minimized.sas"



def read_pddl_task(dom_filename, prob_filename):
    return pddl_parser.open(domain_filename=dom_filename,
                            task_filename=prob_filename)


def get_pddl_file_positions(command):
    positions = []
    for pos, arg in enumerate(command):
        if ".pddl" in arg:
            positions.append(pos)
    assert len(positions) == 2
    return tuple(positions)


def get_pddl_task(state):
    assert "call_strings" in state
    first_command = state["call_strings"].items()[0]
    dom_position, prob_position = get_pddl_file_positions(first_command)
    dom_file = first_command[dom_position]
    prob_file = first_command[prob_position]
    return read_pddl_task(dom_file, prob_file)


def update_pddl_call_strings(state):
    for name, run in list(state["call_strings"].items()):
        dom_position, prob_position = get_pddl_file_positions(run["args"])
        state["call_strings"][name]["args"][dom_position] = NEW_DOMAIN_FILENAME
        state["call_strings"][name]["args"][prob_position] = NEW_PROBLEM_FILENAME
    return state


def read_sas_task(task_filename):
    return sas_file_to_SASTask(task_filename)


def get_sas_file_position(command):
    for pos, arg in enumerate(command):
        if ".sas" in arg:
            return pos


def get_sas_task(state):
    assert "call_strings" in state
    first_command = state["call_strings"].items()[0]
    taskfile_position = get_sas_file_position(first_command)
    sas_file = first_command[taskfile_position]
    return read_sas_task(taskfile_position)

    
def update_sas_call_strings(state):
    state["sas_file"] = NEW_SAS_FILENAME
    return state
