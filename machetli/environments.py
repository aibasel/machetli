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
import pkgutil
import pprint
import re
import subprocess
import time

from machetli import tools, templates
from machetli.evaluator import is_evaluator_successful
from machetli.tools import SubmissionError, TaskError, PollingError, write_state


class Environment:
    """
    Abstract base class of all environments. Concrete environments should
    inherit from this class and override its methods.

    :param allow_nondeterministic_successor_choice:
        When evaluating successors in parallel, situations can occur that are
        impossible in a sequential environment, as results arrive not
        necessarily in the order in which the jobs are started: for example, if
        a state has successors [s1, s2, s3], a successful result for s3 could be
        available before results for s1 are available. Additionally, if the
        evaluation of s2 throws an exception, a sequential evaluation would
        never have evaluated s3. By allowing a non-deterministic successor
        choice (default) the search commits to the first successfully evaluated
        successor even if it would not have come first in a sequential order. If
        the order of the successor generators is important in your case, you can
        switch this off. The search then behaves deterministically, simulating
        sequential execution.

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
    def __init__(self, allow_nondeterministic_successor_choice=True,
                 batch_size=1, loglevel=logging.INFO):
        self.batch_size = batch_size
        self.loglevel = loglevel
        self.allow_nondeterministic_successor_choice = \
            allow_nondeterministic_successor_choice

    def submit(self, batch, batch_id, evaluator_path):
        """
        start evaluating the given batch of successors with the given evaluator.

        :param batch: list of :class:`Successors
            <machetli.successors.Successor>` to be evaluated.

        :param batch_id: increasing ID to identify the batch. Should increase by
            1 in each call.
        
        :param evaluator_path: path to a script that is used to evaluate
            successors. The user documentation contains more information on
            :ref:`how to write an evaluator<usage-evaluator>`.
        """
        raise NotImplementedError

    def wait_until_finished(self):
        """
        Calling this function after submitting a batch of successors will block
        until sufficient results from the batch are available (either an
        successor that the search should commit to, or a negative evaluation of
        all successors in the batch).

        Calling this function before submitting a batch or after the results of
        the batch have been collected is an error.
        """
        raise NotImplementedError

    def get_improving_successor(self):
        """
        Calling this function after waiting will collect the results of the
        batch. Returns either the successor that the search should commit to, or
        None if no such successor was found.

        Calling this function before submitting a batch or waiting for its
        result is an error.
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

    def submit(self, batch, batch_id, evaluator_path):
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
    While running jobs the login nodes periodically checks if all running jobs
    are finished. This constant controls how many seconds to wait before polling
    again.
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
        self.script_path = tools.get_script_path()
        self.job = None

        script_dir = os.path.dirname(self.script_path)
        self.eval_dir = os.path.join(script_dir, "eval_dir")
        tools.makedirs(self.eval_dir)
        if re.search(r"\s+", self.eval_dir):
            logging.critical("The script path must not contain any whitespace characters.")
        self.sbatch_template = resources.read_text(templates, "slurm-array-job.template")
        self.sbatch_filename = os.path.join(script_dir, "slurm-array-job.sbatch")
        self._wait_for_filesystem(self.eval_dir)
        self.critical = False

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

    def submit(self, batch, batch_id, evaluator_path):
        assert not self.job
        try:
            self.job = self._submit_array_job(batch, batch_id, evaluator_path)
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
            self._poll_job()
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
            if self._wait_for_filesystem(result_file):
                if _parse_exit_code(result_file) == 0:
                    successor = task["successor"]
                    break
            else:
                if self.allow_nondeterministic_successor_choice:
                    logging.warning(
                        f"Result file '{result_file}' does not exist. "
                        "Continuing with next task.")
                    continue
                else:
                    logging.warning("Aborting search because evaluation "
                                    f"in '{task['dir']}' failed.")
                    # TODO: raise an error that can be handled by the caller.
                    return None
        self.job = None
        return successor

    def _wait_for_filesystem(self, *paths):
        attempts = int(self.FILESYSTEM_TIME_LIMIT / self.FILESYSTEM_TIME_INTERVAL)
        for _ in range(attempts):
            paths = [path for path in paths if not os.path.exists(path)]
            if not paths:
                return True
            time.sleep(self.FILESYSTEM_TIME_INTERVAL)
        return False  # At least one path from paths does not exist

    def _build_batch_directories(self, batch, batch_num):
        batch_dir_path = os.path.join(
            self.eval_dir, f"batch_{batch_num:03}")
        run_dirs = []
        for rank, successor in enumerate(batch):
            run_dir_name = f"{rank:03}"
            run_dir_path = os.path.join(batch_dir_path, run_dir_name)
            tools.makedirs(run_dir_path)
            state_file_path = os.path.join(run_dir_path, self.STATE_FILENAME)
            write_state(successor.state, state_file_path)
            run_dirs.append(run_dir_path)
        # Give the NFS time to write the paths
        if not self._wait_for_filesystem(*run_dirs):
            logging.critical(
                f"One of the following paths is missing:\n"
                f"{pprint.pformat(run_dirs)}"
            )
        return run_dirs

    def _write_sbatch_file(self, **kwargs):
        dictionary = self._get_job_params()
        dictionary.update(kwargs)
        logging.debug(
            f"Dictionary before filling:\n{pprint.pformat(dictionary)}")
        with open(self.sbatch_filename, "w") as f:
            f.write(self.sbatch_template.format(**dictionary))
        # TODO: Implement check whether file was updated

    def _submit_array_job(self, batch, batch_num, evaluator_path):
        """
        Writes pickled version of each state in *batch* to its own file.
        Then, submits a slurm array job which will evaluate each state
        in parallel. Returns the array job ID of the submitted array job.
        """
        run_dirs = self._build_batch_directories(batch, batch_num)
        batch_name = f"batch_{batch_num:03}"
        self._write_sbatch_file(run_dirs=" ".join(run_dirs), name=batch_name,
                               num_tasks=len(batch)-1,
                               evaluator_path=evaluator_path)
        submission_command = ["sbatch", "--export",
                              ",".join(self.export), self.sbatch_filename]
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

    def _poll_job(self):
        job_id = self.job["id"]
        while True:
            time.sleep(self.POLLING_TIME_INTERVAL)
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
                    if task_state in self.DONE_STATES:
                        done.append(task_id)
                    elif task_state in self.BUSY_STATES:
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
