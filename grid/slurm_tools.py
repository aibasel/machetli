from lab import tools
import pickle
import os
import sys
import subprocess
import re
import time
from lab.environments import BaselSlurmEnvironment, SlurmEnvironment
import logging
import statistics
import pprint

EVAL_DIR = "eval_dir"
DUMP_FILENAME = "dump"
DEFAULT_ARRAY_SIZE = 10
WAITING_SECONDS_FOR_PATH = 10
TIME_LIMIT_FACTOR = 1.5
# The following are sets of slurm job state codes
DONE_STATE = {"COMPLETED"}
BUSY_STATES = {"PENDING", "RUNNING"}


class MinimizerSlurmEnvironment(BaselSlurmEnvironment):
    DEFAULT_NICE = 5000
    ARRAY_JOB_TEMPLATE_FILE = "slurm-array-job.template"
    ARRAY_JOB_FILE = "slurm-array-job.sbatch"
    MAX_MEM_INFAI_BASEL = {"infai_1": "3872M", "infai_2": "6354M"}

    def __init__(self, email=None, extra_options=None, partition=None, qos=None, memory_per_cpu=None, nice=None, export=None, setup=None):
        self.email = email
        self.extra_options = extra_options or "## (not used)"
        self.partition = partition or self.DEFAULT_PARTITION
        self.qos = qos or self.DEFAULT_QOS
        self.memory_per_cpu = memory_per_cpu or self.DEFAULT_MEMORY_PER_CPU
        self.nice = nice or self.DEFAULT_NICE
        self.export = export or self.DEFAULT_EXPORT
        self.setup = setup or self.DEFAULT_SETUP

        # Abort if mem_per_cpu too high for Basel partitions
        if self.partition in {"infai_1", "infai_2"}:
            mem_per_cpu_in_kb = SlurmEnvironment._get_memory_in_kb(
                self.memory_per_cpu)
            max_mem_per_cpu_in_kb = SlurmEnvironment._get_memory_in_kb(
                self.MAX_MEM_INFAI_BASEL[self.partition])
            if mem_per_cpu_in_kb > max_mem_per_cpu_in_kb:
                logging.critical(
                    f"Memory limit {self.memory_per_cpu} surpassing the maximum amount allowed for partition {self.partition}: {self.MAX_MEM_INFAI_BASEL[self.partition]}.")

        eval_root_dir = os.path.dirname(tools.get_script_path())
        template_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_path = os.path.join(
            template_dir, self.ARRAY_JOB_TEMPLATE_FILE)
        self.eval_dir = os.path.join(eval_root_dir, EVAL_DIR)
        tools.makedirs(self.eval_dir)
        self.batchfile_path = os.path.join(self.eval_dir, self.ARRAY_JOB_FILE)
        self.wait_for_filesystem([self.eval_dir])

    def get_job_params(self, name, is_last=False):
        job_params = dict()
        job_params["name"] = name
        job_params["logfile"] = "slurm.log"
        job_params["errfile"] = "slurm.err"
        job_params["partition"] = self.partition
        job_params["qos"] = self.qos
        job_params["memory_per_cpu"] = self.memory_per_cpu
        job_params["soft_memory_limit"] = int(
            0.98 * SlurmEnvironment._get_memory_in_kb(self.memory_per_cpu))
        job_params["nice"] = self.nice
        job_params["extra_options"] = self.extra_options
        job_params["environment_setup"] = self.setup
        if is_last and self.email:
            job_params["mailtype"] = "END,FAIL,REQUEUE,STAGE_OUT"
            job_params["mailuser"] = self.email
        else:
            job_params["mailtype"] = "NONE"
            job_params["mailuser"] = ""
        return job_params

    def wait_for_filesystem(self, paths):
        for _ in paths:
            present = True
            logging.debug("Waiting for filesystem.")
            time.sleep(WAITING_SECONDS_FOR_PATH)
            for path in paths:
                present = present and os.path.exists(path)
            if present:
                logging.info("No path missing.")
                return
        paths_with_newlines = "\n".join(paths) + "\n"
        logging.critical(
            f"One of the following paths is missing:\n{paths_with_newlines}")

    def build_batch_directories(self, batch, batch_num):
        batch_dir_path = os.path.join(
            self.eval_dir, f"batch_{batch_num:03}")
        run_dirs = []
        for rank, state in enumerate(batch):
            run_dir_name = f"{rank:03}"
            run_dir_path = os.path.join(batch_dir_path, run_dir_name)
            tools.makedirs(run_dir_path)
            dump_file_path = os.path.join(run_dir_path, DUMP_FILENAME)
            pickle_and_dump_state(state, dump_file_path)
            run_dirs.append(run_dir_path)
        # Give the NFS time to write the paths
        self.wait_for_filesystem(run_dirs)
        return run_dirs

    def fill_template(self, is_last=False, **kwargs):
        with open(self.template_path, "r") as f:
            template_text = f.read()
        dictionary = self.get_job_params(is_last)
        dictionary.update(kwargs)
        logging.debug(
            f"Dictionary before filling:\n{pprint.pformat(dictionary)}")
        filled_text = template_text % dictionary
        with open(self.batchfile_path, "w") as g:
            g.write(filled_text)
        # TODO: Implement check whether file was updated

    def submit_array_job(self, batch, batch_num):
        """
        Writes pickled version of each state in *batch* to its own file.
        Then, submits a slurm array job which will evaluate each state
        in parallel. Returns the array job ID of the submitted array job.
        """
        # full_runs_path = os.join(tools.get_script_path(), RUNS_DIR
        # tools.makedirs(full_runs_path)
        paths = self.build_batch_directories(batch, batch_num)
        batch_name = f"batch_{batch_num:03}"
        self.fill_template(dump_paths=" ".join(paths), name=batch_name, num_tasks=len(
            batch)-1, python=tools.get_python_executable())
        submission_command = ["sbatch", self.batchfile_path]
        try:
            output = subprocess.check_output(submission_command).decode()
        except subprocess.CalledProcessError as cpe:
            logging.critical(
                f"Submission of batch {batch_name} was not successful.")
        match = re.match(r"Submitted batch job (\d*)", output)
        if not match:
            logging.critical(
                "Something went wrong, no job ID printed after job submission.")
        else:
            logging.info(match.group(0))
        job_id = match.group(1)
        self._poll_job(job_id, batch)
        return paths

    def _poll_job(self, job_id, states):
        avg_sum_of_time_limits = statistics.mean(
            {sum_of_time_limits(s) for s in states})
        job_time_limit = int(TIME_LIMIT_FACTOR * avg_sum_of_time_limits)
        # Let's cut slurm some slack
        time.sleep(2 * WAITING_SECONDS_FOR_PATH)

        start = time.time()
        while (time.time() - start < job_time_limit):
            try:
                output = subprocess.check_output(
                    ["sacct", "-j", str(job_id), "--format=jobid,state", "--noheader", "--allocations"]).decode()
                job_state_dict = self._build_job_state_dict(output)
                done = []
                busy = []
                critical = []
                for detailed_job_id, job_state in job_state_dict.items():
                    if job_state in DONE_STATE:
                        done.append(detailed_job_id)
                    elif job_state in BUSY_STATES:
                        busy.append(detailed_job_id)
                    else:
                        critical.append(detailed_job_id)
                if critical:
                    sub_ids = [parts[1] for parts in (
                        i.split("_") for i in job_state_dict.keys())]
                    logging.critical(
                        f"Evaluation failed for states {', '.join(sub_ids)} in last batch.")
                elif busy:
                    logging.debug(
                        f"Some sub-jobs are still busy:\n{pprint.pformat(job_state_dict)}")
                else:
                    logging.debug("All sub-jobs are done!")
                    return
            except subprocess.CalledProcessError as cpe:
                logging.critical(
                    f"The following error occurred while polling array job {job_id}:\n{cpe}")
            time.sleep(WAITING_SECONDS_FOR_PATH)
        logging.critical(
            f"The allowed time limit of {job_time_limit} s is up and the job did not finish.")

    def _build_job_state_dict(self, sacct_output):
        unclean_job_state_list = sacct_output.strip("\n").split("\n")
        stripped_job_state_list = [pair.strip(
            "+ ") for pair in unclean_job_state_list]
        return {k: v for k, v in (pair.split() for pair in stripped_job_state_list)}


def sum_of_time_limits(state):
    return sum({run.time_limit for run in state["runs"]})


def pickle_and_dump_state(state, file_path):
    with open(file_path, "wb") as dump_file:
        pickle.dump(state, dump_file)


def read_and_unpickle_state(file_path):
    with open(file_path, "rb") as dump_file:
        return pickle.load(dump_file)


def add_result_to_state(result, file_path):
    state = read_and_unpickle_state(file_path)
    state["result"] = result
    pickle_and_dump_state(state, file_path)
    print(f'Result "{result}" was written to state.')


def get_result(file_path):
    time.sleep(5)
    state = read_and_unpickle_state(file_path)
    return state["result"]


def get_next_batch(successor_generator, batch_size=DEFAULT_ARRAY_SIZE):
    batch = []
    for _ in range(batch_size):
        try:
            next_state = next(successor_generator)
            batch.append(next_state)
        except StopIteration:
            return batch
    return batch
