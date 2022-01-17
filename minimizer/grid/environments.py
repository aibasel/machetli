import logging
import os
import pprint
import re
import subprocess
import time

from minimizer import tools
from minimizer.grid import slurm_tools as st


EVAL_DIR = "eval_dir"
DUMP_FILENAME = "dump"
SBATCH_FILE = "slurm-array-job.sbatch"
FILESYSTEM_TIME_INTERVAL = 3
FILESYSTEM_TIME_LIMIT = 60
POLLING_TIME_INTERVAL = 15
TIME_LIMIT_FACTOR = 1.5

# Sets of slurm job state codes
DONE_STATE = {"COMPLETED"}
BUSY_STATES = {"PENDING", "RUNNING", "REQUEUED", "SUSPENDED"}


class SubmissionError(Exception):
    def __init__(self, cpe):
        print(cpe)
        self.returncode = cpe.returncode
        self.cmd = cpe.cmd
        self.output = cpe.output
        self.stdout = cpe.stdout
        self.stderr = cpe.stderr

    def __str__(self):
        return f"""
                Error during job submission:
                Submission command: {self.cmd}
                Returncode: {self.returncode}
                Output: {self.output}
                Captured stdout: {self.stdout}
                Captured stderr: {self.stderr}"""

    def warn(self):
        logging.warning(f"""The following batch submission failed but is ignored:
                        {self}""")

    def warn_abort(self):
        logging.warning(f"""Task order cannot be kept because the following batch submission failed:
                        {self}
                        Aborting search.""")


class TaskError(Exception):
    def __init__(self, critical_tasks):
        self.critical_tasks = critical_tasks
        self.indices_critical = [int(parts[1]) for parts in (
            task_id.split("_") for task_id in self.critical_tasks)]

    def __repr__(self):
        return pprint.pformat(self.critical_tasks)

    def remove_critical_tasks(self, job):
        """Remove tasks from job that entered a critical state."""
        job["tasks"] = [t for i, t in enumerate(
            job["tasks"]) if i not in self.indices_critical]
        logging.warning(
            f"Some tasks from job {job['id']} entered a critical state but the search is continued.")

    def remove_tasks_after_first_critical(self, job):
        """Remove all tasks from job after the first one that entered a critical state."""
        first_failed = self.indices_critical[0]
        job["tasks"] = job["tasks"][:first_failed]
        if not job["tasks"]:
            logging.warning(f"""Since the first task failed, the order cannot be kept.
                            Aborting search.""")
        else:
            logging.warning(f"""At least one task from job {job['id']} entered a critical state:
                            {self}
                            The tasks before the first critical one are still considered.""")


class PollingError(Exception):
    def warn_abort(self, job):
        logging.error(
            f"Polling job {job['id']} caused an error. Aborting search.")


class Environment:
    def __init__(self, email=None):
        self.email = email


class LocalEnvironment(Environment):
    pass


def makedirs(path):
    """
    os.makedirs() variant that doesn't complain if the path already exists.
    """
    try:
        os.makedirs(path)
    except OSError:
        # Directory probably already exists.
        pass


class SlurmEnvironment(Environment):
    # Must be overridden in derived classes.
    DEFAULT_PARTITION = None
    DEFAULT_QOS = None
    DEFAULT_MEMORY_PER_CPU = None

    # Can be overridden in derived classes.
    DEFAULT_EXPORT = ["PATH"]
    DEFAULT_SETUP = ""
    DEFAULT_NICE = 0  # TODO: Check if this makes sense

    def __init__(
        self,
        extra_options=None,
        partition=None,
        qos=None,
        memory_per_cpu=None,
        nice=None,
        export=None,
        setup=None,
        **kwargs
    ):
        Environment.__init__(self, **kwargs)

        self.extra_options = extra_options or "## (not used)"
        self.partition = partition or self.DEFAULT_PARTITION
        self.qos = qos or self.DEFAULT_QOS
        self.memory_per_cpu = memory_per_cpu or self.DEFAULT_MEMORY_PER_CPU
        self.nice = nice or self.DEFAULT_NICE
        self.export = export or self.DEFAULT_EXPORT
        self.setup = setup or self.DEFAULT_SETUP
        self.script_path = tools.get_script_path()

        # Number of cores is used to determine the soft memory limit
        self.cpus_per_task = 1  # This is the default
        if "--cpus-per-task" in self.extra_options:
            rexpr = r"--cpus-per-task=(\d+)"
            match = re.search(rexpr, self.extra_options)
            assert match, f"{self.extra_options} should have matched {rexpr}."
            self.cpus_per_task = int(match.group(1))

        script_dir = os.path.dirname(self.script_path)
        self.eval_dir = os.path.join(script_dir, EVAL_DIR)
        makedirs(self.eval_dir)
        st.check_for_whitespace(self.eval_dir)
        self.sbatch_file = os.path.join(script_dir, SBATCH_FILE)
        self.wait_for_filesystem(self.eval_dir)

    def get_job_params(self):
        job_params = dict()
        job_params["logfile"] = "slurm.log"
        job_params["errfile"] = "slurm.err"
        job_params["partition"] = self.partition
        job_params["qos"] = self.qos
        job_params["memory_per_cpu"] = self.memory_per_cpu
        job_params["nice"] = self.nice
        job_params["extra_options"] = self.extra_options
        job_params["environment_setup"] = self.setup
        job_params["mailtype"] = "NONE"
        job_params["mailuser"] = ""
        job_params["soft_memory_limit"] = int(
            0.98 * self.cpus_per_task * self._get_memory_in_kb(
                self.memory_per_cpu))
        job_params["python"] = tools.get_python_executable()
        job_params["script_path"] = self.script_path
        return job_params

    def wait_for_filesystem(self, *paths):
        attempts = int(FILESYSTEM_TIME_LIMIT / FILESYSTEM_TIME_INTERVAL)
        for _ in range(attempts):
            time.sleep(FILESYSTEM_TIME_INTERVAL)
            paths = [path for path in paths if not os.path.exists(path)]
            if not paths:
                return True
        return False  # At least one path from paths does not exist

    def build_batch_directories(self, batch, batch_num):
        batch_dir_path = os.path.join(
            self.eval_dir, f"batch_{batch_num:03}")
        run_dirs = []
        for rank, state in enumerate(batch):
            run_dir_name = f"{rank:03}"
            run_dir_path = os.path.join(batch_dir_path, run_dir_name)
            makedirs(run_dir_path)
            dump_file_path = os.path.join(run_dir_path, DUMP_FILENAME)
            st.pickle_and_dump_state(state, dump_file_path)
            run_dirs.append(run_dir_path)
        # Give the NFS time to write the paths
        if not self.wait_for_filesystem(*run_dirs):
            logging.critical(
                f"One of the following paths is missing:\n{pprint.pformat(run_dirs)}")
        return run_dirs

    def write_sbatch_file(self, **kwargs):
        dictionary = self.get_job_params()
        dictionary.update(kwargs)
        logging.debug(
            f"Dictionary before filling:\n{pprint.pformat(dictionary)}")
        filled_text = st.fill_template(**dictionary)
        with open(self.sbatch_file, "w") as f:
            f.write(filled_text)
        # TODO: Implement check whether file was updated

    def submit_array_job(self, batch, batch_num):
        """
        Writes pickled version of each state in *batch* to its own file.
        Then, submits a slurm array job which will evaluate each state
        in parallel. Returns the array job ID of the submitted array job.
        """
        run_dirs = self.build_batch_directories(batch, batch_num)
        batch_name = f"batch_{batch_num:03}"
        self.write_sbatch_file(run_dirs=" ".join(run_dirs), name=batch_name,
                               num_tasks=len(batch)-1)
        submission_command = ["sbatch", "--export",
                              ",".join(self.export), self.sbatch_file]
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
        job = {"id": job_id}
        job["tasks"] = [{"curr": c, "dir": d} for c, d in zip(batch, run_dirs)]
        return job

    def poll_job(self, job_id):
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
                    logging.info(
                        f"{len(busy)} task{'s are' if len(busy) > 1 else ' is'} still busy.")
                    continue
                if critical:
                    critical_tasks = [
                        task for task in task_states if task in critical]
                    raise TaskError(critical_tasks)
                else:
                    logging.info("All tasks are done!")
                    return
            except subprocess.CalledProcessError as cpe:
                raise PollingError

    def _build_task_state_dict(self, sacct_output):
        unclean_job_state_list = sacct_output.strip("\n").split("\n")
        stripped_job_state_list = [pair.strip(
            "+ ") for pair in unclean_job_state_list]
        return {k: v for k, v in (pair.split() for pair in stripped_job_state_list)}

    @staticmethod
    def _get_memory_in_kb(limit):
        match = re.match(r"^(\d+)(k|m|g)?$", limit, flags=re.I)
        if not match:
            logging.critical(f"malformed memory_per_cpu parameter: {limit}")
        memory = int(match.group(1))
        suffix = match.group(2)
        if suffix is not None:
            suffix = suffix.lower()
        if suffix == "k":
            pass
        elif suffix is None or suffix == "m":
            memory *= 1024
        elif suffix == "g":
            memory *= 1024 * 1024
        return memory


class BaselSlurmEnvironment(SlurmEnvironment):
    """Environment for Basel's AI group."""
    DEFAULT_PARTITION = "infai_1"
    DEFAULT_QOS = "normal"
    DEFAULT_MEMORY_PER_CPU = "3872M"
    MAX_MEM_INFAI_BASEL = {"infai_1": "3872M", "infai_2": "6354M"}
    DEFAULT_NICE = 5000

    def __init__(self, **kwargs):
        SlurmEnvironment.__init__(self, **kwargs)

        # Abort if mem_per_cpu too high for Basel partitions
        if self.partition in {"infai_1", "infai_2"}:
            mem_per_cpu_in_kb = self._get_memory_in_kb( self.memory_per_cpu)
            max_mem_per_cpu_in_kb = self._get_memory_in_kb(
                self.MAX_MEM_INFAI_BASEL[self.partition])
            if mem_per_cpu_in_kb > max_mem_per_cpu_in_kb:
                logging.critical(
                    f"Memory limit {self.memory_per_cpu} surpassing the maximum amount allowed for partition {self.partition}: {self.MAX_MEM_INFAI_BASEL[self.partition]}.")

