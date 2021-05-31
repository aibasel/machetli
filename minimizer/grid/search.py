from collections.abc import Iterable
import logging
import os

from minimizer.grid import slurm_tools as st
from minimizer.grid.environments import SubmissionError, TaskError, PollingError


RESULT = "result"


def search_grid(initial_state, successor_generators, environment, enforce_order, batch_size):
    if not isinstance(successor_generators, Iterable):
        successor_generators = [successor_generators]
    current_state = initial_state
    batch_num = -1
    for SG in successor_generators:
        while True:
            sg = SG().get_successors(current_state)

            for state_batch in st.get_next_batch(sg, batch_size):
                batch_num += 1

                # Submit batch
                try:
                    job = environment.submit_array_job(state_batch, batch_num)
                except SubmissionError as se:
                    if not enforce_order:
                        se.warn()
                        continue  # Continue with next batch
                    else:
                        se.warn_abort()
                        return current_state

                # Poll job state
                try:
                    environment.poll_job(job["id"])
                except TaskError as te:
                    if not enforce_order:
                        te.remove_critical_tasks(job)
                        if not job["tasks"]:
                            continue
                    else:  # only consider successors before first successor with failed task
                        te.remove_tasks_after_first_critical(job)
                        if not job["tasks"]:
                            return current_state
                except PollingError as pe:
                    pe.warn_abort(job)
                    return current_state

                # Check evaluated successor states
                for task in job["tasks"]:
                    result_file = os.path.join(task["dir"], RESULT)
                    # Result file is not present
                    if not environment.wait_for_filesystem(result_file):
                        if not enforce_order:
                            logging.warning(
                                f"Result file {result_file} does not exist. Continuing with next task.")
                            continue
                        else:
                            logging.warning(
                                f"Aborting search because evaluation in {task['dir']} failed.")
                            return current_state
                    else:  # Result file is present
                        result = st.parse_result(result_file)
                        if result:
                            logging.info("Found successor!")
                            current_state = task["curr"]
                            break
                if result:  # Leave batch loop and continue with new successor generator
                    break

            else:  # Exhausted all batches of current_state, leave while loop
                break
    return current_state
