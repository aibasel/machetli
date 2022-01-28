from itertools import islice
from minimizer.tools import SubmissionError, TaskError, PollingError


"""
When performing the search on a Slurm grid, the possibility of
failure at some point is increased due to the introduced parallelism
on multiple nodes and an I/O load over the network filesystem. When
setting *allow_nondeterministic_successor_choice* to ``False``, the
:func:`search <minimizer.search.search>` function will enforce that
the search is aborted if a single task fails and no successor from
an earlier task is accepted.
"""
def search(initial_state, successor_generator, evaluator, environment):
    current_state = initial_state
    batch_size = environment.batch_size
    batch_num = 0

    successors = successor_generator.get_successors(current_state)
    batch = list(islice(successors, batch_size))
    while batch:
        try:
            environment.submit(batch, batch_num, evaluator)
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
