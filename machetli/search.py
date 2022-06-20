from itertools import islice
import logging

from machetli.environments import LocalEnvironment
from machetli.successors import make_single_successor_generator
from machetli.tools import SubmissionError, TaskError, PollingError, configure_logging


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
    batch_size = environment.batch_size
    batch_num = 0

    successors = successor_generator.get_successors(current_state)
    batch = list(islice(successors, batch_size))
    while batch:
        try:
            environment.submit(batch, batch_num, evaluator_path)
            environment.wait_until_finished()
            successor = environment.get_improving_successor()
        except (SubmissionError, TaskError, PollingError):
            # FIXME: this is not proper error handling yet.
            successor = None

        if successor:
            logging.info(successor.change_msg)
            current_state = successor.state
            successors = successor_generator.get_successors(current_state)
        batch_num += 1
        batch = list(islice(successors, batch_size))

    logging.info("No improving successor found, terminating search.")
    return current_state
