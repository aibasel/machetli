import logging
import time

from machetli.environments import LocalEnvironment, EvaluationTask
from machetli.errors import SubmissionError, PollingError
from machetli.successors import make_single_successor_generator
from machetli.tools import batched, configure_logging


def search(initial_state, successor_generator, evaluator_path, environment=None):
    """Start a Machetli search and return the resulting state.

    The search is started from the *initial state* and *successor generators*
    are then used to create transformed instances. Each instance created this
    way is evaluated with the given *evaluator* that checks if the behavior we
    are interested in is still present in the transformed instance. The search
    always commits to the transformation of the first instance where the
    evaluator succeeds (first-choice hill climbing).
    
    :param initial_state: is a dictionary describing the instance you want to
        simplify. The internal format of this dictionary has to match what the
        successor generators expect. Modules that include successor generators
        also provide a function to create an initial state in the correct
        format.

    :param successor_generator: is a single :class:`SuccessorGenerator
        <machetli.successors.SuccessorGenerator>` or a list of
        SuccessorGenerators. If a list [s1, ..., sn] is given, the search first
        tries all successors from s1, then from s2, and so on.

    :param evaluator_path: is the path to a Python file that contains a function
        *evaluate(state)* that is used to check if the behaviour that the search
        is analyzing is still present in the state. The function has to take a
        single parameter that is the state of the search as a dictionary like
        the one given to *search* as the *initial_state* parameter. It has to
        return True if the behaviour is present and False otherwise. The
        documentation has addition information on :ref:`how to write an
        evaluator <usage-evaluator>`.
        
    :param environment: determines how the search should be executed. If no
        environment is specified, a :class:`LocalEnvironment
        <machetli.environments.LocalEnvironment>` is used that executes
        everything on sequence on the local machine. Alternatively, an
        implementation of :class:`SlurmEnvironment
        <machetli.environments.SlurmEnvironment>` can be used to parallelize the
        search on a cluster running the Slurm engine.

    :return: the last state where the evaluator was successful, i.e., all
        successors of the resulting state no longer have the evaluated property.

    .. note:: 
        The initial state is never checked to have the evaluated property.
        If the result of the search is identical to the initial
        state, this can have two reasons: 

        1. The initial state is minimal with respect to the evaluated property
           and the used successor generators. In this case, you can try
           repeating the search with additional successor generators.
        2. The initial state does not have the property and neither does any of
           its successors. (If a successor has the property despite the initial
           state not having it, Machetli will nevertheless minimize the task as
           intended.) If you started from an instance that should have the
           property, this could indicate a bug in your evaluator script, which
           either doesn't reproduce the property correctly, or fails to
           recognize it.

    :Example:

    .. code-block:: python
        :linenos:
        :emphasize-lines: 4

        initial_state = sas.generate_initial_state("bugged.sas")
        evaluator_filename = os.path.join(os.path.dirname(tools.get_script_path()), "evaluator.py")

        result = search(initial_state, [sas.RemoveVariables(), sas.RemoveOperators()], evaluator_filename)

        sas.write_file(result, "result.sas")


    """
    if environment is None:
        environment = LocalEnvironment()
    configure_logging(environment.loglevel)
    successor_generator = make_single_successor_generator(successor_generator)

    logging.info("Starting search ...")
    current_state = initial_state
    while True:
        successors = successor_generator.get_successors(current_state)
        try:
            improving_state, message = _get_improving_successor(
                evaluator_path, successors, environment)
        except SubmissionError as e:
            logging.critical(f"Terminating search because job submission for successor evaluation failed:\n{e}")
        except PollingError as e:
            logging.critical(f"Terminating search because querying the status of a submitted successor evaluation failed:\n{e}")

        if message:
            logging.info(message)
        if improving_state:
            current_state = improving_state
        else:
            return current_state


def _get_improving_successor(evaluator_path, successors, environment):
    report_if_no_improvement = set()
    def on_task_completed(job_id, task):
        if environment.allow_nondeterministic_successor_choice:
            # If an evaluation reports a non-improving successor,
            # deterministic mode considers the next successor. In all
            # other cases (improving successor, evaluation did not
            # finish correctly), there is no need to evaluate later
            # successors.
            if task.status != EvaluationTask.DONE_AND_NOT_IMPROVING:
                environment.cancel(job_id, after=task)
        else: # non-deterministic mode
            if task.status == EvaluationTask.DONE_AND_IMPROVING:
                # We found an improving successor, so all other
                # evaluations can be canceled.
                environment.cancel(job_id)
            elif task.status == EvaluationTask.OUT_OF_RESOURCES:
                report_if_no_improvement.add(task)
            elif (task.status == EvaluationTask.CRITICAL):
                logging.warn(f"Critical error in task {job_id}_{task.task_id}: {task.error}")

    for batch in batched(successors, environment.batch_size):
        tasks = environment.run(evaluator_path, batch, on_task_completed)
        for task in tasks:
            if task.status == EvaluationTask.DONE_AND_NOT_IMPROVING:
                continue
            elif task.status == EvaluationTask.DONE_AND_IMPROVING:
                return task.successor.state, task.successor.change_msg
            elif not environment.allow_nondeterministic_successor_choice:
                return None, (
                    "Errors occurred in successor evaluations before finding "
                    "an improving successor. With the option "
                    "`allow_nondeterministic_successor_choice` an improving "
                    "successor found later would not count.")

    message = "No improving successor was found."
    if report_if_no_improvement:
        run_dirs = [task.run_dir for task in report_if_no_improvement]
        run_dirs_str = "\n".join(sorted(run_dirs))
        message += (
            f" Note that the following tasks ran out of resources and thus "
            f" could not successfully be checked:\n{run_dirs_str}")
    return None, message
