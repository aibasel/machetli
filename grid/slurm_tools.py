from lab import tools
import pickle
import os

EVAL_DIR = "eval_dir"

DEFAULT_ARRAY_SIZE = 10
DEFAULT_PARTITION = "infai_1"
DEFAULT_QOS = "normal"
DEFAULT_MEMORY_PER_CPU = "3872M"
# ARRAY_JOB_HEADER_TEMPLATE_FILE = "slurm-array-job-header"
# ARRAY_JOB_BODY_TEMPLATE_FILE = "slurm-array-job-body"
ARRAY_JOB_FILE = "slurm-array-job.sbatch"
ARRAY_JOB_TEMPLATE = "slurm-array-job.template"


def build_batch_directories(batch, batch_num)
    script_path = tools.get_script_path()
    eval_path = os.path.join(script_path, EVAL_DIR)
    dump_paths = []
    for dir_num in range(batch_num):
        dump_dir_name = f"{dir_num:05}"
        dump_path = os.path.join(eval_path, dump_dir_name)
        dump_paths.append(dump_path)
        tools.makedirs(dump_path)
    return dump_paths


def submit_array_job(batch, batch_num):
    """
    Writes pickled version of each state in *batch* to its own file.
    Then, submits a slurm array job which will evaluate each state
    in parallel. Returns the array job ID of the submitted array job.
    """
    # full_runs_path = os.join(tools.get_script_path(), RUNS_DIR
    # tools.makedirs(full_runs_path)
    paths = build_batch_directories(batch, batch_num)
    submission_command = ["sbatch"]

    pass


def get_next_batch(successor_generator, batch_size=3):
    batch = []
    for _ in range(batch_size):
        try:
            next_state = next(successor_generator)
            batch.append(next_state)
        except StopIteration:
            return batch
    return batch