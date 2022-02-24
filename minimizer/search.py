from itertools import islice
from minimizer.tools import SubmissionError, TaskError, PollingError


def search(initial_state, successor_generator, evaluator_path, environment):
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
