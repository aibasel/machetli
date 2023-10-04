"""
Environments determine how Machetli executes its search. In a local environment,
everything is executed sequentially on your local machine. However, the search
can also be parallelized in a grid environment. In that case multiple successors
of a state will be evaluated in parallel on the compute nodes of the grid with
the main search running on the login node, generating successors and dispatching
and waiting for jobs. 
"""

from importlib import resources
import logging
import os
from pathlib import Path
import pprint
import re
import subprocess
import time

from machetli import tools, templates
from machetli.errors import SubmissionError, PollingError, \
    format_called_process_error
from machetli.evaluator import is_evaluator_successful
from machetli.tools import write_state


class EvaluationTask():
    PENDING = "pending"
    DONE_AND_IMPROVING = "improving"
    DONE_AND_NOT_IMPROVING = "not improving"
    OUT_OF_RESOURCES = "ran out of resources"
    CRITICAL = "critical"
    CANCELED = "canceled"

    def __init__(self, successor, successor_id, run_dir):
        self.successor = successor
        self.successor_id = successor_id
        self.run_dir = run_dir
        self.status = self.PENDING
        self.error_msg = ""


class Environment:
    """
    Abstract base class of all environments. Concrete environments should
    inherit from this class and override its methods.

    :param batch_size:
        Number of successors evaluated in parallel. No effect on sequential
        environments.

    :param loglevel:
        Amount of logging output to generate. Use constants from the module
        :mod:`logging` to control the level of detail in the logs.

        * `DEBUG`: detailed information usually only useful during development
        * `INFO` (default): provides feedback on the execution of the program
        * `WARNING`: silent unless something unexpected happens
        * `ERROR`: silent unless an error occured that causes the search to
          terminate
        * `CRITICAL`: silent unless the program crashes

    """
    def __init__(self, batch_size=1, loglevel=logging.INFO):
        self.batch_size = batch_size
        self.loglevel = loglevel

    def run(self, evaluator_path, successors, on_task_completed):
        """
        evaluate the given successors with the given evaluator. The evaluator is
        run on all successors (possibly in parallel, depending on the
        environment). Every time an evaluation of a successor is completed, the
        callback `on_task_completed` is called.

        :param evaluator_path: path to a script that is used to evaluate a
            successor. The user documentation contains more information on
            :ref:`how to write an evaluator<usage-evaluator>`.
        
        :param successors: list of :class:`Successors
            <machetli.successors.Successor>` to be evaluated.

        :param on_task_completed: callback function that will be called once for
            each successor after its evaluation is completed. The callback
            receives an :class:`EvaluationTask` as its only parameter that
            describes the result of the evaluation. As evaluations could be
            performed in parallel, the order in which the evaluations complete
            is not necessarily deterministic. The callback may return a list of
            indices into `successors` to indicate that those successors need not
            be evaluated any more.
        """
        raise NotImplementedError


class LocalEnvironment(Environment):
    """
    This environment evaluates all successors sequentially on the local machine.

    See :class:`Environment` for inherited options.
    """
    def __init__(self, **kwargs):
        Environment.__init__(self, **kwargs)
        self.successor = None

    def submit(self, batch, evaluator_path):
        assert self.successor is None

        for succ in batch:
            # TODO: react to self.allow_nondeterministic_successor_choice by ignoring evaluator crashes?
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
    """
    This environment evaluates multiple successors in parallel on the compute nodes
    of a cluster accessed through the Slurm grid engine.

    :param email:
        Email address for notification once the search finished
    :param extra_options:
        Additional options passed to the Slurm script
    :param partition:
        Slurm partition to use for job submission
    :param qos:
        Slurm QOS to use for job submission
    :param memory_per_cpu:
        Memory limit per CPU to use for Slurm job
    :param cpus_per_task:
        Number of CPUs to reserve for evaluating a single successor
    :param nice:
        Nice value to use for Slurm jobs (higher nice value = lower priority).
    :param export:
        Environment variables to export from the login node to the compute nodes.
    :param setup:
        Additional bash script to set up the compute nodes (loading modules, etc.).
    :param batch_size: (default 200)
        Number of successors evaluated in parallel.

    See :class:`Environment` for inherited options.
    """

    DEFAULT_PARTITION = None
    """
    Slurm partition to use for job submission if no other partition is passed to
    the constructor. Must be overridden in derived classes.
    """
    DEFAULT_QOS = None
    """
    Slurm QOS to use for job submission if no other QOS is passed to the
    constructor. Must be overridden in derived classes.
    """
    DEFAULT_MEMORY_PER_CPU = None
    """
    Memory limit per CPU to use for Slurm job if no limit is passed to the
    constructor. Must be overridden in derived classes.
    """

    DEFAULT_EXPORT = ["PATH"]
    """
    Environment variables to export from the login node to the compute nodes.
    May be overridden in derived classes or with a constructor argument.
    """
    DEFAULT_SETUP = ""
    """
    Additional bash script to set up the compute nodes (loading modules, etc.).
    May be overridden in derived classes or with a constructor argument.
    """
    DEFAULT_NICE = 0
    """
    Nice value to use for Slurm jobs (higher nice value = lower priority).
    May be overridden in derived classes or with a constructor argument.
    """

    STATE_FILENAME = "state.pickle"
    """
    Filename for stored states. States are written to disk and loaded on the
    compute nodes (assuming a shared file system of the compute and login
    nodes). 
    """

    # Sets of slurm job state codes
    DONE_STATES = {"COMPLETED"}
    """
    Slurm status codes that indicate that a job successfully terminated.
    """
    BUSY_STATES = {"PENDING", "RUNNING", "REQUEUED", "SUSPENDED"}
    """
    Slurm status codes that indicate that a job has not yet terminated.
    """

    FILESYSTEM_TIME_INTERVAL = 3
    """
    Files that one node writes are not necessarily immediately available on
    all other nodes. If a file we expect to be there is not found, we check again
    after waiting for some seconds.
    """
    FILESYSTEM_TIME_LIMIT = 60
    """
    When a file is not found after repeated checks, we eventually give up and
    treat this as an error. This constant controls after how many seconds to
    give up.
    """
    POLLING_TIME_INTERVAL = 15
    """
    While running jobs the login node periodically checks the status of all
    pending tasks. This constant controls how many seconds to wait before
    polling again.
    """

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
        self.script_path = Path(tools.get_script_path())

        script_dir = self.script_path.parent
        self.eval_dir = Path(script_dir/"eval_dir")
        if re.search(r"\s+", self.eval_dir):
            logging.critical("The script path must not contain any whitespace characters.")
        # TODO: continue from existing directory, or handle possible error.
        self.eval_dir.mkdir(parents=True, exist_ok=False)
        self._wait_for_filesystem(self.eval_dir)
        self.sbatch_template = resources.read_text(templates, "slurm-array-job.template")
        self.sbatch_filename = os.path.join(script_dir, "slurm-array-job.sbatch")
        self.batch_id = 0

    def run(self, evaluator_path: Path, batch, on_task_finished):
        job_id, tasks = self._submit(evaluator_path, batch)
        pending_task_ids = set(range(len(batch)))
        while pending_task_ids:
            time.sleep(self.POLLING_TIME_INTERVAL)
            self._update_status(job_id, tasks)
            pending_tasks_changed = True
            while pending_tasks_changed:
                pending_tasks_changed = False
                for task_id in set(pending_task_ids):
                    task = tasks[task_id]
                    if task.status != EvaluationTask.PENDING:
                        pending_task_ids.remove(task_id)
                        ids_to_cancel = on_task_finished(task)
                        if ids_to_cancel:
                            self._cancel(job_id, tasks, ids_to_cancel)
                        pending_tasks_changed = True
            if pending_task_ids:
                logging.info(
                    f"{len(pending_task_ids)} task"
                    f"{'s are' if len(pending_task_ids) > 1 else ' is'} still busy.")
        return tasks

    def _cancel(self, job_id, tasks, ids_to_cancel):
        # TODO only cancel tasks with status == PENDING and update their status to CANCELED
        pass

    def _get_job_params(self):
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
        job_params["state_filename"] = self.STATE_FILENAME
        return job_params

    def _submit(self, batch, evaluator_path: Path):
        assert not self.current_job
        """
        Writes pickled version of each state in *batch* to its own file.
        Then, submits a slurm array job which will evaluate each state
        in parallel. Returns the array job ID of the submitted array job.
        """
        self.batch_id += 1
        batch_name = f"batch_{self.batch_id:03}"
        job_name = f"{evaluator_path.stem}_{batch_name}"
        tasks = self._build_batch_directories(batch, batch_name)
        self._write_sbatch_file(tasks=tasks,
                                name=job_name,
                                num_tasks=len(batch)-1,
                                evaluator_path=evaluator_path)
        submission_command = ["sbatch", "--export",
                              ",".join(self.export), self.sbatch_filename]
        try:
            output = subprocess.check_output(submission_command).decode()
        except subprocess.CalledProcessError as cpe:
            raise SubmissionError(format_called_process_error(cpe))

        match = re.match(r"Submitted batch job (\d*)", output)
        if not match:
            raise SubmissionError(
                "Something went wrong, no job ID printed after job submission.")

        job_id = match.group(1)
        logging.info(f"Submitted batch job {job_id}")
        return job_id, tasks

    def _wait_for_filesystem(self, *paths):
        attempts = int(self.FILESYSTEM_TIME_LIMIT / self.FILESYSTEM_TIME_INTERVAL)
        for _ in range(attempts):
            paths = [path for path in paths if not os.path.exists(path)]
            if not paths:
                return True
            time.sleep(self.FILESYSTEM_TIME_INTERVAL)
        return False  # At least one path from paths does not exist

    def _build_batch_directories(self, batch, batch_name):
        batch_dir = self.eval_dir/batch_name
        tasks = []
        for task_id, successor in enumerate(batch):
            run_dir = batch_dir/f"{task_id:03}"
            # TODO: raise SubmissionError when directory exists
            run_dir.mkdir(parents=True, exists_ok=False)
            write_state(successor.state, run_dir/self.STATE_FILENAME)
            tasks.append(EvaluationTask(successor.state, task_id, run_dir))

        run_dirs = [t.run_dir for t in tasks]
        # Give the NFS time to write the paths
        if not self._wait_for_filesystem(*run_dirs):
            logging.critical(
                f"One of the following paths is missing:\n"
                f"{pprint.pformat(run_dirs)}"
            )
        return tasks

    def _write_sbatch_file(self, tasks, **kwargs):
        dictionary = self._get_job_params()
        dictionary.update(kwargs)
        dictionary["run_dirs"] = " ".join([str(t.run_dir) for t in tasks])
        logging.debug(
            f"Dictionary before filling:\n{pprint.pformat(dictionary)}")
        with open(self.sbatch_filename, "w") as f:
            f.write(self.sbatch_template.format(**dictionary))
        # TODO: Implement check whether file was updated

    def _get_slurm_status(self, job_id):
        try:
            output = subprocess.check_output(
                ["sacct", "-j", str(job_id), "--format=jobid,state",
                 "--noheader", "--allocations"]).decode()
        except subprocess.CalledProcessError as cpe:
            raise PollingError(format_called_process_error(cpe))

        status_by_task_id = {}
        pattern = re.compile(r"(?P<job_id>\d+)_(?P<task_id>\d+)\+?\s+(?P<status>\w+)\+?")
        for line in output.splitlines():
            m = re.match(pattern, line)
            if m:
                assert m.group("job_id") == job_id
                task_id = m.group("task_id")
                status = m.group("status")
                status_by_task_id[task_id] = status
            else:
                raise PollingError(
                    "Invalid format when querying `sacct` for task status.\n" +
                    output)
        return status_by_task_id

    def _update_status(self, job_id, tasks):
        status_by_task_id = self._get_slurm_status(job_id)
        for task in tasks:
            try:
                slurm_status = status_by_task_id[task.task_id]
            except IndexError:
                raise PollingError(
                    f"Did not find status of slurm job {job_id}_{task.task_id}.")

            if slurm_status in self.DONE_STATES:
                result_file = task.run_dir/"exit_code"
                self._wait_for_filesystem(result_file)
                try:
                    exit_code = _parse_exit_code(result_file)
                except IOError:
                    task.status = EvaluationTask.CRITICAL
                    task.error = f"Missing exit code file '{str(result_file)}'"
                    continue
                if exit_code == EXIT_CODE_IMPROVING:
                    task.status = EvaluationTask.DONE_AND_IMPROVING
                elif exit_code == EXIT_CODE_NOT_IMPROVING:
                    task.status = EvaluationTask.DONE_AND_NOT_IMPROVING
                elif exit_code == EXIT_CODE_TIMEOUT:
                    task.status = EvaluationTask.OUT_OF_RESOURCES
                elif exit_code == EXIT_CODE_MEMOUT:
                    task.status = EvaluationTask.OUT_OF_RESOURCES
                else:
                    task.status = EvaluationTask.CRITICAL
                    task.error = f"Unexpected exit code {exit_code}"
            elif slurm_status in self.BUSY_STATES:
                task.status = EvaluationTask.PENDING
            else:
                task.status = EvaluationTask.CRITICAL
                task.error = f"Unexpected Slurm status '{slurm_status}'"

            logging.debug(
                f"Task status of {job_id}_{task.task_id} is {task.status} (slurm: {slurm_status})")

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
    """
    Environment for Basel's AI group. This will only be useful if you are
    running Machetli on the grid in Basel. If you want to specialize
    :class:`SlurmEnvironment<machetli.environments.SlurmEnvironment>` for your
    grid, use this class as a template.

    See :class:`SlurmEnvironment` for inherited options.
    """
    DEFAULT_PARTITION = "infai_1"
    """
    Unless otherwise specified, we execute jobs on partition "infai_1".
    To change this use `partition="infai_2"` in the constructor.
    """
    DEFAULT_QOS = "normal"
    """
    All jobs run in QOS group "normal".
    """
    DEFAULT_MEMORY_PER_CPU = "3872M"
    """
    Unless otherwise specified, we reserve 3.8 GB of memory per core which is
    available on both partitions. 
    To change this use `memory_per_cpu` in the constructor and either run on
    "infai_2" (up to 6354 MB) or reserve more cores per task.
    """
    MAX_MEM_INFAI_BASEL = {"infai_1": "3872M", "infai_2": "6354M"}
    """
    Maximally available memory per CPU on the infai partitions.
    """
    DEFAULT_NICE = 5000
    """
    We schedule all jobs with a nice value of 5000 so autonice has the option to
    adjust it.
    """

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
