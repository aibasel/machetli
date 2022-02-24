from itertools import islice
from minimizer.successors import make_single_successor_generator
from minimizer.tools import SubmissionError, TaskError, PollingError, configure_logging



def search(initial_state, successor_generator, evaluator_path, environment):
    """Start a minimizer search and return the resulting state.

    The search is started from *initial_state*, which is a dictionary
    describing the initial conditions of what you want to minimize.
    
    *successor_generator* is a single class name whose implementation defines
    how successors of a state are generated. Successor generators must
    implement the :class:`SuccessorGenerator
    <minimizer.planning.generators.SuccessorGenerator>` class.

    *evaluator_path* is the path to a Python file that contains a function
    *evaluate(state)* that is used to check if the behaviour that the search
    is analyzing is still present in state. The function has to take a single
    parameter that is the state of the search as a dictionary like the one given
    to *search* as the *initial_state* parameter. It has to return True if the
    behaviour is present and False otherwise.

    *environment* determines whether the search should be done on a
    local machine or on a Slurm computing grid. Use
    :class:`minimizer.grid.environments.LocalEnvironment` or an
    implementation of
    :class:`minimizer.grid.environments.SlurmEnvironment`.

    Example usage:

    .. literalinclude:: ../examples/issue335_PDDL/local_test.py
        :language: python
        :caption:
        :lines: 18-30
        :emphasize-lines: 9-12
    """
    configure_logging(environment.loglevel)
    successor_generator = make_single_successor_generator(successor_generator)

    current_state = initial_state
    batch_size = environment.batch_size
    batch_num = 0

    successors = successor_generator.get_successors(current_state)
    batch = list(islice(successors, batch_size))
    while batch:
        try:
            environment.submit(batch, batch_num, evaluator_path)
            environment.wait_until_finished()
            best_successor = environment.get_improving_successor()
        except (SubmissionError, TaskError, PollingError):
            # FIXME: this is not proper error handling yet.
            best_successor = None

        if best_successor:
            current_state = best_successor
            successors = successor_generator.get_successors(current_state)
        batch_num += 1
        batch = list(islice(successors, batch_size))

    return current_state
