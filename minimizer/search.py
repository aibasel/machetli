from itertools import chain, islice
from minimizer.tools import SubmissionError, TaskError, PollingError


def search(initial_state, successor_generator, evaluator, environment):
    current_state = initial_state
    batch_size = environment.batch_size
    batch_num = 0

    successors = successor_generator.get_successors(current_state)
    batch = list(islice(successors, batch_size))
    while batch:
        # TODO: we could also split this into *submit*, *poll*, and
        #  *evaluate*. The *batch_size* of *LocalEnvironment* should
        #  then rather be *1* than *None*, but *poll* doesn't make too
        #  much sense in that case.
        try:
            best_successor = environment.get_improving_successor(
                evaluator, batch, batch_num)
        except (SubmissionError, TaskError, PollingError):
            # TODO: this might not be reasonable error treatment, but it
            #  is what happened previously
            best_successor = None

        if best_successor:
            current_state = best_successor
            successors = successor_generator.get_successors(current_state)
        batch_num += 1
        batch = list(islice(successors, batch_size))

    return current_state
