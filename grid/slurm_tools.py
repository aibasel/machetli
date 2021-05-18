import argparse
import logging
import os
import pickle
import platform
import pprint
import re
import subprocess
import sys
import time

from grid import slurm_tools
from lab import tools
from lab.environments import BaselSlurmEnvironment, SlurmEnvironment
# import statistics TODO: import can probably be deleted

DRIVER_ERR = "driver.err"
EVAL_DIR = "eval_dir"
DUMP_FILENAME = "dump"
DEFAULT_ARRAY_SIZE = 10
FILESYSTEM_TIME_INTERVAL = 3
FILESYSTEM_TIME_LIMIT = 60
POLLING_TIME_INTERVAL = 15
TIME_LIMIT_FACTOR = 1.5
# The following are sets of slurm job state codes
DONE_STATE = {"COMPLETED"}
BUSY_STATES = {"PENDING", "RUNNING"}


def search_grid(initial_state, successor_generators, environment, enforce_order=False):
    if not isinstance(successor_generators, list):
        successor_generators = [successor_generators]
    env = environment
    state = initial_state
    batch_num = 0
    for succ_gen in successor_generators:
        while True:
            successor_generator = succ_gen().get_successors(state)
            batch_of_successors = slurm_tools.get_next_batch(
                successor_generator)
            if not batch_of_successors:
                break
            try:
                job_id, run_dirs = env.submit_array_job(
                    batch_of_successors, batch_num)
                env.poll_job(job_id, batch_of_successors)
            except slurm_tools.SubmissionError as e:
                if not enforce_order:
                    logging.warning(
                        f"The following batch submission failed but is ignored:\n{e}")
                else:
                    logging.critical(
                        f"Order cannot be kept because the following batch submission failed:\n{e}")
            except slurm_tools.TaskError as e:
                indices_critical_tasks = [int(parts[1]) for parts in (
                    job_id.split("_") for job_id in e.critical_tasks)]
                if not enforce_order:
                    # remove successors and their directories if their task entered a critical state
                    batch_of_successors = [b for i, b in enumerate(
                        batch_of_successors) if i not in indices_critical_tasks]
                    run_dirs = [r for i, r in enumerate(
                        run_dirs) if not i in indices_critical_tasks]

                    logging.warning(
                        f"At least one task from job {job_id} entered a critical state but is ignored:\n{e}")
                else:
                    # since order needs to be enforced, only consider successors before first successor with failed task
                    first_failed_index = indices_critical_tasks[0]
                    batch_of_successors = batch_of_successors[:first_failed_index]
                    run_dirs = run_dirs[:first_failed_index]
                    if first_failed_index == 0:  # the task of the first successor entered a critical state
                        logging.critical(
                            f"At least the first task from job {job_id} entered a critical state and the search is aborted.\n{e}")
                    else:
                        logging.warning(f"""At least one task from job {job_id} entered a critical state.
                        The successors before the first one whose task entered the critical state are still considered.\n{e}""")
            for succ, run_dir in zip(batch_of_successors, run_dirs):
                driver_err_file = os.path.join(run_dir, slurm_tools.DRIVER_ERR)
                if os.path.exists(driver_err_file):
                    if enforce_order:
                        logging.warning(
                            f"Evaluation failed for state in {run_dir}. No further successor is considered.")
                        break
                    else:
                        logging.warning(
                            f"Evaluation failed for state in {run_dir}. Continuing search.")
                        result = False
                else:
                    dump_file = os.path.join(
                        run_dir, slurm_tools.DUMP_FILENAME)
                    result = slurm_tools.get_result(dump_file)
                if result:
                    logging.info("Found successor!")
                    state = succ
                    break
            else:
                break
            batch_num += 1
    return state


def get_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", action="store_true")
    parser.add_argument("--evaluate", type=str, metavar="PATH_TO_STATE_DUMP")
    parser.add_argument("--debug", action="store_true")
    return parser


def main(initial_state, successor_generators, evaluator, environment, enforce_order=False):
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    tools.configure_logging() if not args.debug else tools.configure_logging(
        level=logging.DEBUG)

    if args.evaluate:
        logging.debug(f"Python interpreter: {tools.get_python_executable()}")
        dump_file_path = args.evaluate
        state = slurm_tools.read_and_unpickle_state(dump_file_path)
        state["cwd"] = os.path.dirname(dump_file_path)
        result = evaluator().evaluate(state)
        del state["cwd"]
        slurm_tools.add_result_to_state(result, dump_file_path)
        logging.info(f"Node: {platform.node()}")
        sys.exit(0)
    elif args.grid:
        return search_grid(initial_state, successor_generators, environment)
    else:
        arg_parser.print_usage()


class SubmissionError(Exception):
    def __init__(self, cpe):
        self.returncode = cpe.returncode
        self.cmd = cpe.command
        self.stdout = cpe.stdout
        self.stderr = cpe.stderr

    def __str__(self):
        return pprint.pformat(
            {
                "Submission command": self.cmd,
                "Returncode": self.returncode,
                "Stdout": self.stdout,
                "Stderr": self.stderr
            }
        )


class TaskError(Exception):
    def __init__(self, critical_tasks):
        self.critical_tasks = critical_tasks

    def __str__(self):
        return pprint.pformat(self.critical_tasks)


class MinimizerSlurmEnvironment(BaselSlurmEnvironment):
    DEFAULT_NICE = 5000
    ARRAY_JOB_TEMPLATE_FILE = "slurm-array-job.template"
    ARRAY_JOB_FILE = "slurm-array-job.sbatch"
    MAX_MEM_INFAI_BASEL = {"infai_1": "3872M", "infai_2": "6354M"}

    def __init__(self, email=None, extra_options=None, partition=None, qos=None, memory_per_cpu=None, nice=None, export=None, setup=None):
        self.script_path = tools.get_script_path()
        self.email = email
        self.extra_options = extra_options or "## (not used)"
        self.partition = partition or self.DEFAULT_PARTITION
        self.qos = qos or self.DEFAULT_QOS
        self.memory_per_cpu = memory_per_cpu or self.DEFAULT_MEMORY_PER_CPU
        self.nice = nice or self.DEFAULT_NICE
        self.export = export or self.DEFAULT_EXPORT
        self.setup = setup or self.DEFAULT_SETUP

        # Number of cores is used to determine the soft memory limit
        self.cpus_per_task = 1  # This is the default
        if "--cpus-per-task" in self.extra_options:
            rexpr = r"--cpus-per-task=(\d+)"
            match = re.search(rexpr, self.extra_options)
            assert match, f"{self.extra_options} should have matched {rexpr}."
            self.cpus_per_task = int(match.group(1))

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
        logging.debug(f"Eval root dir:{eval_root_dir}")
        logging.debug(f"Template dir:{template_dir}")
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
        job_params["nice"] = self.nice
        job_params["extra_options"] = self.extra_options
        job_params["environment_setup"] = self.setup
        if is_last and self.email:
            job_params["mailtype"] = "END,FAIL,REQUEUE,STAGE_OUT"
            job_params["mailuser"] = self.email
        else:
            job_params["mailtype"] = "NONE"
            job_params["mailuser"] = ""
        job_params["soft_memory_limit"] = int(
            0.98 * self.cpus_per_task * SlurmEnvironment._get_memory_in_kb(self.memory_per_cpu))
        job_params["python"] = tools.get_python_executable()
        job_params["script_path"] = self.script_path
        return job_params

    def wait_for_filesystem(self, paths):
        attempts = int(FILESYSTEM_TIME_LIMIT / FILESYSTEM_TIME_INTERVAL)
        for _ in range(attempts):
            time.sleep(FILESYSTEM_TIME_INTERVAL)
            paths = [path for path in paths if not os.path.exists(path)]
            if not paths:
                logging.debug("No path missing.")
                return
        logging.critical(
            f"The following paths are missing:\n{pprint.pformat(paths)}")

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
        self.fill_template(dump_paths=" ".join(paths), name=batch_name,
                           num_tasks=len(batch)-1)
        submission_command = ["sbatch", "--export",
                              ",".join(self.export), self.batchfile_path]
        try:
            output = subprocess.check_output(submission_command).decode()
        except subprocess.CalledProcessError as cpe:
            raise SubmissionError(cpe)
        match = re.match(r"Submitted batch job (\d*)", output)
        if not match:
            logging.critical(
                "Something went wrong, no job ID printed after job submission.")
        else:
            logging.info(match.group(0))
        job_id = match.group(1)
        return job_id, paths

    def poll_job(self, job_id, states):
        while True:
            time.sleep(POLLING_TIME_INTERVAL)
            try:
                output = subprocess.check_output(
                    ["sacct", "-j", str(job_id), "--format=jobid,state", "--noheader", "--allocations"]).decode()
                task_states = self._build_task_state_dict(output)
                done = []
                busy = []
                critical = []
                logging.debug(f"Task states:\n{pprint.pformat(task_states)}")
                for task_id, task_state in task_states.items():
                    if task_state in DONE_STATE:
                        done.append(task_id)
                    elif task_state in BUSY_STATES:
                        busy.append(task_id)
                    else:
                        critical.append(task_id)
                if busy:
                    continue
                if critical:
                    critical_tasks = {
                        task for task in task_states if task in critical}
                    raise TaskError(critical_tasks)
                else:
                    logging.debug("All tasks are done!")
                    return
            except subprocess.CalledProcessError as cpe:
                logging.critical(
                    f"The following error occurred while polling array job {job_id}:\n{cpe}")

    def _build_task_state_dict(self, sacct_output):
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
