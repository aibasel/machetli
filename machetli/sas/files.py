import logging
from pathlib import Path
from pickle import PickleError
import sys
from typing import Union

from machetli.sas.constants import KEY_IN_STATE
from machetli.sas.sas_tasks import SASTask, SASVariables, SASMutexGroup, \
    SASInit, SASGoal, SASOperator, SASAxiom

from machetli import tools
from machetli.evaluator import EXIT_CODE_CRITICAL, EXIT_CODE_BEHAVIOR_PRESENT, \
    EXIT_CODE_BEHAVIOR_NOT_PRESENT


def generate_initial_state(sas_file: Union[Path, str]) -> dict:
    r"""
    Parse the SAS\ :sup:`+` task defined in the SAS\ :sup:`+` file
    `sas_file` and return an initial state containing the parsed
    SAS\ :sup:`+` task.

    :return: a dictionary pointing to the SAS\ :sup:`+` task specified
             in the file `sas_file`.
    """
    return {
        KEY_IN_STATE: _read_task(Path(sas_file))
    }


def _run_evaluator_on_sas_file(evaluate, sas_path):
    if evaluate(sas_path):
        sys.exit(EXIT_CODE_BEHAVIOR_PRESENT)
    else:
        sys.exit(EXIT_CODE_BEHAVIOR_NOT_PRESENT)


def run_evaluator(evaluate):
    r"""
    Load the state passed to the script via its command line arguments, then run
    the given function *evaluate* on the SAS\ :sup:`+` file encoded in the
    state, and exit the program with the appropriate exit code. If the function
    returns ``True``, use
    :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>`,
    otherwise use
    :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_NOT_PRESENT>`.
    In addition to running the evaluator, this function creates the SAS\ :sup:`+`
    file as 'task.sas' in the current directory.

    This function is meant to be used as the main function of an evaluator
    script. Instead of a path to the state, the command line arguments can also
    be paths to a SAS\ :sup:`+` file. This is meant for testing and debugging
    the evaluator directly on SAS\ :sup:`+` input.

    :param evaluate: is a function taking the filename of a SAS\ :sup:`+` file as
        input and returning ``True`` if the specified behavior occurs for the
        given instance, and ``False`` if it doesn't. Other ways of exiting the
        function (exceptions, ``sys.exit`` with exit codes other than
        :attr:`EXIT_CODE_BEHAVIOR_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_PRESENT>` or
        :attr:`EXIT_CODE_BEHAVIOR_NOT_PRESENT<machetli.evaluator.EXIT_CODE_BEHAVIOR_NOT_PRESENT>`)
        are treated as failed evaluations by the search.
    """
    if len(sys.argv) == 2:
        path = Path(sys.argv[1])
        try:
            state = tools.read_state(path)
            write_file(state, "task.sas")
            _run_evaluator_on_sas_file(evaluate, "task.sas")
        except (FileNotFoundError, PickleError):
            _run_evaluator_on_sas_file(evaluate, path)
    else:
        logging.critical(
            "Error: evaluator has to be called with either a path to a pickled "
            "state, or a path to a SAS^+ file.")
        sys.exit(EXIT_CODE_CRITICAL)


def _read_task(sas_file : Path) -> SASTask:
    lines = (l for l in sas_file.read_text().splitlines())
    while True:
        line = next(lines)
        if line == "begin_metric":
            break
    metric = bool(next(lines))
    assert next(lines) == "end_metric"
    # read variables
    num_vars = int(next(lines))
    variables = _read_variables(lines, num_vars)
    # read mutexes
    num_mutexes = int(next(lines))
    mutexes = _read_mutexes(lines, num_mutexes)
    # read init state
    init = _read_init_state(lines, num_vars)
    # read goal
    goal = _read_goal(lines)
    # read operators
    num_operators = int(next(lines))
    operators = _read_operators(lines, num_operators)
    # read axioms
    num_axioms = int(next(lines))
    axioms = _read_axioms(lines, num_axioms)

    sas_task = SASTask(variables, mutexes, init, goal, operators, axioms, metric)
    sas_task.validate()
    return sas_task


def _read_variables(lines, num_vars):
    axiom_layers = []
    ranges = []
    value_name_lists = []
    for _ in range(num_vars):
        assert next(lines) == "begin_variable"
        next(lines)  # skip variable name
        axiom_layers.append(int(next(lines)))
        num_values = int(next(lines))
        ranges.append(num_values)
        value_names = []
        for _ in range(num_values):
            value_names.append(next(lines))
        value_name_lists.append(value_names)
        assert next(lines) == "end_variable"
    return SASVariables(ranges, axiom_layers, value_name_lists)


def _read_mutexes(lines, num_mutexes):
    mutexes = []
    for _ in range(num_mutexes):
        assert next(lines) == "begin_mutex_group"
        num_facts = int(next(lines))
        facts = []
        for _ in range(num_facts):
            var, val = map(int, next(lines).split(" "))
            facts.append((var, val))
        mutexes.append(SASMutexGroup(facts))
        assert next(lines) == "end_mutex_group"
    return mutexes


def _read_init_state(lines, num_vars):
    init = []
    assert next(lines) == "begin_state"
    for _ in range(num_vars):
        val = int(next(lines))
        init.append(val)
    assert next(lines) == "end_state"
    return SASInit(init)


def _read_goal(lines):
    assert next(lines) == "begin_goal"
    num_pairs = int(next(lines))
    pairs = []
    for _ in range(num_pairs):
        var, val = map(int, next(lines).split(" "))
        pairs.append((var, val))
    assert next(lines) == "end_goal"
    return SASGoal(pairs)


def _read_operators(lines, num_operators):
    operators = []
    for _ in range(num_operators):
        assert next(lines) == "begin_operator"
        name = "(" + next(lines) + ")"
        num_prevail_conditions = int(next(lines))
        prevail_conditions = []
        for _ in range(num_prevail_conditions):
            var, val = map(int, next(lines).split(" "))
            prevail_conditions.append((var, val))
        num_effects = int(next(lines))
        pre_post = []
        for _ in range(num_effects):
            effect_line = list(map(int, next(lines).split(" ")))
            num_effect_conditions = effect_line[0]
            cond = []
            for cond_num in range(1, 2 * num_effect_conditions, 2):
                var = effect_line[cond_num]
                val = effect_line[cond_num + 1]
                cond.append((var, val))
            var, pre, post = effect_line[-3:]
            pre_post.append((var, pre, post, cond))
        cost = int(next(lines))
        operators.append(SASOperator(name, prevail_conditions, pre_post, cost))
        assert next(lines) == "end_operator"
    return operators


def _read_axioms(lines, num_axioms):
    axioms = []
    for _ in range(num_axioms):
        assert next(lines) == "begin_rule"
        length_body = int(next(lines))
        condition = []
        for _ in range(length_body):
            var, val = map(int, next(lines).split(" "))
            condition.append((var, val))
        effect_line = list(map(int, next(lines).split(" ")))
        var = effect_line[0]
        val = effect_line[2]
        assert 1 - val == effect_line[1]
        effect = (var, val)
        axioms.append(SASAxiom(condition, effect))
        assert next(lines) == "end_rule"
    return axioms


def write_file(state: dict, path: Union[Path, str]):
    """
    Write the problem represented in `state` to disk.
    """
    with Path(path).open("w") as file:
        state[KEY_IN_STATE].output(file)
