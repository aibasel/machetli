from lab import tools
import pickle
import os
import sys
import subprocess
import re

EVAL_DIR = "eval_dir"

DEFAULT_ARRAY_SIZE = 3
DEFAULT_PARTITION = "infai_1"
DEFAULT_QOS = "normal"
DEFAULT_MEMORY_PER_CPU = "3872M"
DEFAULT_NICE = 5000
# DEFAULT_MAIL_TYPE = "END,FAIL,REQUEUE,STAGE_OUT"
# ARRAY_JOB_HEADER_TEMPLATE_FILE = "slurm-array-job-header"
# ARRAY_JOB_BODY_TEMPLATE_FILE = "slurm-array-job-body"
ARRAY_JOB_FILE = "slurm-array-job.sbatch"
ARRAY_JOB_TEMPLATE = "slurm-array-job.template"


def write_pickled_state_to_dir(state, dir):
    with open(os.path.join(dir, "dump"), "wb") as dump:
        pickle.dump(state, dump)


def build_batch_directories(batch, batch_num):
    script_dir = os.path.dirname(tools.get_script_path())
    eval_dir_path = os.path.join(script_dir, EVAL_DIR)
    batch_dir_path = os.path.join(script_dir, EVAL_DIR, f"batch_{batch_num:05}")
    dump_dirs = []
    for rank, state in enumerate(batch):
        dump_dir_name = f"{rank:05}"
        dump_dir_path = os.path.join(batch_dir_path, dump_dir_name)
        tools.makedirs(dump_dir_path)
        write_pickled_state_to_dir(state, dump_dir_path)
        dump_dirs.append(dump_dir_path)
    return dump_dirs


def fill_template(**kwargs):
    script_dir = os.path.dirname(tools.get_script_path())
    template_path = os.path.join(script_dir, ARRAY_JOB_TEMPLATE)
    f = open(template_path, "r")
    template_text = f.read()
    f.close()
    values_dict = {
        "name": "test",
        "logfile": "out.log",
        "errfile": "out.err",
        "partition": DEFAULT_PARTITION,
        "qos": DEFAULT_QOS,
        "memory_per_cpu": DEFAULT_MEMORY_PER_CPU,
        "num_tasks": DEFAULT_ARRAY_SIZE - 1,
        "nice": str(DEFAULT_NICE),
        "mailtype": "NONE",
        "mailuser": ""
    }
    values_dict.update(**kwargs)
    filled_text = template_text % values_dict
    batchfile_path = os.path.join(script_dir, ARRAY_JOB_FILE)
    g = open(batchfile_path, "w")
    g.write(filled_text)
    g.close()
    return batchfile_path


def submit_array_job(batch, batch_num):
    """
    Writes pickled version of each state in *batch* to its own file.
    Then, submits a slurm array job which will evaluate each state
    in parallel. Returns the array job ID of the submitted array job.
    """
    # full_runs_path = os.join(tools.get_script_path(), RUNS_DIR
    # tools.makedirs(full_runs_path)
    paths = build_batch_directories(batch, batch_num)
    batchfile_path = fill_template(dump_paths=" ".join(paths))
    submission_command = ["sbatch", batchfile_path]
    # ____________________
    # for testing purposes
    print(submission_command)
    sys.exit(0)
    # ____________________
    output = subprocess.check_output(submission_command).decode()
    match = re.match(r"Submitted batch job (\d*)", output)
    assert match, f"Submitting job with sbatch failed: '{output}'"
    return (match.group(1), paths)


def get_next_batch(successor_generator, batch_size=DEFAULT_ARRAY_SIZE):
    batch = []
    for _ in range(batch_size):
        try:
            next_state = next(successor_generator)
            batch.append(next_state)
        except StopIteration:
            return batch
    return batch


def let_job_finish(job_id):
    pass

# for testing purposes
batch = [{str(i): i} for i in range(10)]
submit_array_job(batch, 12)