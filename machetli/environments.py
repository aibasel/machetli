import logging
import os
import pkgutil
import pprint
import re
import subprocess
import time

from machetli import tools
from machetli.evaluator import is_evaluator_successful
from machetli.tools import SubmissionError, TaskError, PollingError, write_state


EVAL_DIR = "eval_dir"
STATE_FILENAME = "state.pickle"

TEMPLATE_FILE = "slurm-array-job.template"
SBATCH_FILE = "slurm-array-job.sbatch"

FILESYSTEM_TIME_INTERVAL = 3
FILESYSTEM_TIME_LIMIT = 60
POLLING_TIME_INTERVAL = 15
TIME_LIMIT_FACTOR = 1.5

# Sets of slurm job state codes
DONE_STATE = {"COMPLETED"}
BUSY_STATES = {"PENDING", "RUNNING", "REQUEUED", "SUSPENDED"}


"""
When performing the search on a Slurm grid, the possibility of
failure at some point is increased due to the introduced parallelism
on multiple nodes and an I/O load over the network filesystem. When
setting *allow_nondeterministic_successor_choice* to ``False``, the
:func:`search <machetli.search.search>` function will enforce that
the search is aborted if a single task fails and no successor from
an earlier task is accepted.
"""
class Environment:
    def __init__(self, allow_nondeterministic_successor_choice=True,
                 batch_size=1, loglevel=logging.INFO):
        self.batch_size = batch_size
        self.loglevel = loglevel
        self.allow_nondeterministic_successor_choice = \
            allow_nondeterministic_successor_choice

    def submit(self, batch, batch_id, evaluator_path):
        raise NotImplementedError

    def wait_until_finished(self):
        raise NotImplementedError

    def get_improving_successor(self):
        raise NotImplementedError


class LocalEnvironment(Environment):
    def __init__(self, **kwargs):
        Environment.__init__(self, **kwargs)
        self.successor = None

    def submit(self, batch, batch_id, evaluator_path):
        assert self.successor is None

        for succ in batch:
            if is_evaluator_successful(evaluator_path, succ.state):
                self.successor = succ
            break

    def wait_until_finished(self):
        pass

    def get_improving_successor(self):
        result = self.successor
        self.successor = None
        return result


class SlurmEnvironment(Environment):
    # Must be overridden in derived classes.
    DEFAULT_PARTITION = None
    DEFAULT_QOS = None
    DEFAULT_MEMORY_PER_CPU = None

    # Can be overridden in derived classes.
    DEFAULT_EXPORT = ["PATH"]
    DEFAULT_SETUP = ""
    DEFAULT_NICE = 0

    # TODO: are differences to Lab reasonable? e.g., here we have no time limit.
    def __init__(
        self,
        email=None,
        extra_options=None,
        partition=None,
        qos=None,
        memory_per_cpu=None,
        cpus_per_task=1,
        nice=None,
        export=None,
        setup=None,
        batch_size=200,
        **kwargs
    ):
        Environment.__init__(self, batch_size=batch_size, **kwargs)

        self.email = email
        self.extra_options = extra_options or "## (not used)"
        self.partition = partition or self.DEFAULT_PARTITION
        self.qos = qos or self.DEFAULT_QOS
        self.memory_per_cpu = memory_per_cpu or self.DEFAULT_MEMORY_PER_CPU
        self.cpus_per_task = cpus_per_task
        self.nice = nice or self.DEFAULT_NICE
        self.export = export or self.DEFAULT_EXPORT
        self.setup = setup or self.DEFAULT_SETUP
        self.script_path = tools.get_script_path()
        self.job = None

        script_dir = os.path.dirname(self.script_path)
        self.eval_dir = os.path.join(script_dir, EVAL_DIR)
        tools.makedirs(self.eval_dir)
        if re.search(r"\s+", self.eval_dir):
            logging.critical("The script path must not contain any whitespace characters.")
        self.sbatch_file = os.path.join(script_dir, SBATCH_FILE)
        self.wait_for_filesystem(self.eval_dir)
        self.critical = False

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

    def submit(self, batch, batch_id, evaluator_path):
        assert not self.job
        try:
            self.job = self.submit_array_job(batch, batch_id, evaluator_path)
        except SubmissionError as se:
            if self.allow_nondeterministic_successor_choice:
                se.warn_abort()
                # TODO: this means job is undefined, so we should also abort.
            else:
                se.warn()
                self.job = None
                raise se

    def wait_until_finished(self):
        assert self.job
        try:
            self.poll_job()
        except TaskError as te:
            if self.allow_nondeterministic_successor_choice:
                te.remove_critical_tasks(self.job)
                if not self.job["tasks"]:
                    # TODO: this is just a hack to replace the "continue"
                    #  that occurred here in the original grid search.
                    self.critical = True
                    return
            else:
                te.remove_tasks_after_first_critical(self.job)
                if not self.job["tasks"]:
                    self.job = None
                    raise te
        except PollingError as pe:
            pe.warn_abort()
            raise pe

    def get_improving_successor(self):
        assert self.job
        if self.critical:
            self.critical = False
            self.job = None
            return None

        successor = None
        for task in self.job["tasks"]:
            result_file = os.path.join(task["dir"], "exit_code")
            if self.wait_for_filesystem(result_file):
                if _parse_exit_code(result_file) == 0:
                    successor = task["successor"]
                    break
            else:
                if self.allow_nondeterministic_successor_choice:
                    logging.warning(
                        f"Result file {result_file} does not exist. "
                        "Continuing with next task.")
                    continue
                else:
                    logging.warning("Aborting search because evaluation "
                                    f"in {task['dir']} failed.")
                    # TODO: raise an error that can be handled by the caller.
                    return None
        self.job = None
        return successor

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
        for rank, successor in enumerate(batch):
            run_dir_name = f"{rank:03}"
            run_dir_path = os.path.join(batch_dir_path, run_dir_name)
            tools.makedirs(run_dir_path)
            state_file_path = os.path.join(run_dir_path, STATE_FILENAME)
            write_state(successor.state, state_file_path)
            run_dirs.append(run_dir_path)
        # Give the NFS time to write the paths
        if not self.wait_for_filesystem(*run_dirs):
            logging.critical(
                f"One of the following paths is missing:\n"
                f"{pprint.pformat(run_dirs)}"
            )
        return run_dirs

    def write_sbatch_file(self, **kwargs):
        dictionary = self.get_job_params()
        dictionary.update(kwargs)
        logging.debug(
            f"Dictionary before filling:\n{pprint.pformat(dictionary)}")
        filled_text = _fill_template(**dictionary)
        with open(self.sbatch_file, "w") as f:
            f.write(filled_text)
        # TODO: Implement check whether file was updated

    def submit_array_job(self, batch, batch_num, evaluator_path):
        """
        Writes pickled version of each state in *batch* to its own file.
        Then, submits a slurm array job which will evaluate each state
        in parallel. Returns the array job ID of the submitted array job.
        """
        run_dirs = self.build_batch_directories(batch, batch_num)
        batch_name = f"batch_{batch_num:03}"
        self.write_sbatch_file(run_dirs=" ".join(run_dirs), name=batch_name,
                               num_tasks=len(batch)-1,
                               evaluator_path=evaluator_path)
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
        # TODO: This is strange.
        job = {"id": job_id,
               "tasks": [{"successor": s, "dir": d} for s, d in
                         zip(batch, run_dirs)]}
        return job

    def poll_job(self):
        job_id = self.job["id"]
        while True:
            time.sleep(POLLING_TIME_INTERVAL)
            try:
                output = subprocess.check_output(
                    ["sacct", "-j", str(job_id), "--format=jobid,state",
                     "--noheader", "--allocations"]).decode()
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
                        f"{len(busy)} task"
                        f"{'s are' if len(busy) > 1 else ' is'} still busy.")
                    continue
                if critical:
                    critical_tasks = [
                        task for task in task_states if task in critical]
                    raise TaskError(critical_tasks)
                else:
                    logging.info("Batch completed.")
                    return
            except subprocess.CalledProcessError:
                raise PollingError(job_id)

    def _build_task_state_dict(self, sacct_output):
        unclean_job_state_list = sacct_output.strip("\n").split("\n")
        stripped_job_state_list = [pair.strip(
            "+ ") for pair in unclean_job_state_list]
        return {k: v for k, v in
                (pair.split() for pair in stripped_job_state_list)}

    @staticmethod
    # This function is copied from lab.environment.SlurmEnvironment
    # (<https://lab.readthedocs.org>).
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



def _parse_exit_code(result_file):
    with open(result_file, "r") as rf:
        exitcode = int(rf.read())
    return exitcode


def _fill_template(**parameters):
    template = tools.get_string(pkgutil.get_data(
        "machetli", os.path.join("templates", TEMPLATE_FILE)))
    return template.format(**parameters)


## TODO: call this when the search is done.
def _launch_email_job(email):
    try:
        subprocess.run(["sbatch",
                        "--job-name='Search terminated'",
                        "--mail-type=BEGIN",
                        f"--mail-user={email}"],
                    input=b"#! /bin/bash\n")
    except:
        logging.warning(
            "Something went wrong while trying to send the "
            "notification email.")


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
                    f"Memory limit {self.memory_per_cpu} surpassing the "
                    f"maximum amount allowed for partition {self.partition}: "
                    f"{self.MAX_MEM_INFAI_BASEL[self.partition]}."
                )
