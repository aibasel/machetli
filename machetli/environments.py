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
from pathlib import Path
import pprint
import re
import subprocess
import time

from machetli import tools, templates
from machetli.errors import SubmissionError, PollingError, \
    format_called_process_error
from machetli.evaluator import EXIT_CODE_BEHAVIOR_PRESENT, \
    EXIT_CODE_BEHAVIOR_NOT_PRESENT, EXIT_CODE_RESOURCE_LIMIT
from machetli.successors import Successor
from machetli.tools import write_state, run


class EvaluationTask():
    """
    An EvaluationTask represents the evaluation of one successor and carries
    information about the current status of that evaluation.
    """

    PENDING = "pending"
    """
    Status of tasks from the time they are started until they stop for any reason.
    """
    DONE_AND_BEHAVIOR_PRESENT = "behavior present"
    """
    Status of tasks that successfully evaluated their successor and showed that
    this successor exhibits the behavior that the evaluator is checking for.
    """
    DONE_AND_BEHAVIOR_NOT_PRESENT = "behavior not present"
    """
    Status of tasks that successfully evaluated their successor but showed that
    this successor does not exhibit the behavior that the evaluator is checking for.
    """
    OUT_OF_RESOURCES = "ran out of resources"
    """
    Status of tasks that failed to evaluate their successor because the
    evaluation ran out of time or memory.
    """
    CRITICAL = "critical"
    """
    Status of tasks that failed to evaluate their successor because the evaluation
    stopped for an unknown reason, such as crashing the evaluation script.
    """
    CANCELED = "canceled"
    """
    Status of tasks that were canceled by Machetli. This happens if the search
    determines that the evaluation of their successor is not needed.
    """

    def __init__(self, successor, successor_id, run_dir):
        self.successor = successor
        self.successor_id = successor_id
        self.run_dir = run_dir
        self.status = self.PENDING
        self.error_msg = ""


class EvaluationJob():
    """
    An EvaluationJob consists of several :class:`EvaluationTasks
    <machetli.environments.EvaluationTask>`. It represents the evaluation of a
    batch of successors and carries information about the current status of that
    evaluation.
    """

    def __init__(self, name, evaluator_path, batch_dir, tasks):
        self.name = name
        self.evaluator_path = evaluator_path
        self.batch_dir = batch_dir
        self.tasks = tasks


def _update_completed_task_status(task, exit_code):
    if exit_code == EXIT_CODE_BEHAVIOR_PRESENT:
        task.status = EvaluationTask.DONE_AND_BEHAVIOR_PRESENT
    elif exit_code == EXIT_CODE_BEHAVIOR_NOT_PRESENT:
        task.status = EvaluationTask.DONE_AND_BEHAVIOR_NOT_PRESENT
    elif exit_code == EXIT_CODE_RESOURCE_LIMIT:
        # TODO: We closed issue66, so this would need another reference.
        # TODO issue66: Detect running out of resources correctly:
        # the process cannot always report this with a custom exit code because
        # it is killed when it runs out of resources. Maybe handle it in
        # the slurm wrapper or check for exit codes produced by signals here?
        task.status = EvaluationTask.OUT_OF_RESOURCES
    elif "TimeoutExpired" in (task.run_dir/"run.err").read_text():
        task.status = EvaluationTask.OUT_OF_RESOURCES
    # TODO: We closed issue66, so we should resolve this or change the reference.
    elif False: # TODO issue66 (detect memouts)
        task.status = EvaluationTask.OUT_OF_RESOURCES
    else:
        task.status = EvaluationTask.CRITICAL
        task.error_msg = f"Evaluator ended with unexpected exit code {exit_code}."


class Environment:
    """
    Abstract base class of all environments. Concrete environments should
    inherit from this class and override its methods.

    :param batch_size:
        Number of successors evaluated in one batch. Environments always
        complete the evaluation of one batch of successors before considering
        successors from the next batch. Each batch is written to disk in one
        directory, with one subdirectory for each successor.

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

    STATE_FILENAME = "state.pickle"
    """
    Filename for stored states. States are written to disk and loaded for
    evaluation. In grid environments, this assumes a shared file system for
    login and compute nodes.
    """

    def __init__(self, batch_size=1, loglevel=logging.INFO):
        # TODO: this is accidentally doing what we want: in interactive python sessions
        # we don't have a script path and want to use the name of the current working directory
        # as the experiment name. This is what get_script_path returns, but this is coincidental.
        script_path = tools.get_script_path()
        self.exp_name = script_path.stem
        self.eval_dir = script_path.parent / f"{self.exp_name}-eval"
        if re.search(r"\s+", str(self.eval_dir)):
            logging.critical("The script path must not contain any whitespace characters.")

        self.iteration_id = 0
        self.batch_id = 0
        self.batch_size = batch_size
        self.loglevel = loglevel
        self.initial_state = None
        self.initial_state_run_dir = None

    def start_new_iteration(self):
        """
        Notifies the environment that a new iteration is starting. This is
        relevant for grouping the tasks of one iteration together on the disk.
        """
        self.iteration_id += 1
        self.batch_id = 0

    def _start_new_batch(self) -> tuple[Path, str]:
        self.batch_id += 1
        iteration_name = f"iteration_{self.iteration_id:05}"
        batch_name = f"batch_{self.batch_id:05}"
        job_name = f"{self.exp_name}-{iteration_name}-{batch_name}"
        batch_dir = self.eval_dir/iteration_name/batch_name
        return batch_dir, job_name

    def _populate_run_dir(self, batch_dir, task_id, state) -> Path:
        run_dir = batch_dir/f"{task_id:05}"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise SubmissionError(
                f"Could not create run_dir at '{run_dir}'. Do you have old "
                f"experiment data at '{self.eval_dir}'?")
        write_state(state, run_dir/self.STATE_FILENAME)
        return run_dir


    def _prepare_job(self, evaluator_path, batch) -> EvaluationJob:
        """
        Creates a run directory for each successor in *batch* and writes a
        pickled version of the state to disk. Returns an EvaluationJob that
        represents the current status of this batch's evaluation.
        """
        batch_dir, job_name = self._start_new_batch()
        tasks = []
        for task_id, successor in enumerate(batch):
            run_dir = self._populate_run_dir(batch_dir, task_id, successor.state)
            tasks.append(EvaluationTask(successor, task_id, run_dir))
        return EvaluationJob(job_name, evaluator_path, batch_dir, tasks)

    def _run_job(self, job, on_task_completed) -> list[EvaluationTask]:
        raise NotImplementedError

    def remember_initial_state(self, initial_state):
        """
        Store the initial state in a run directory. This is used by the search to
        evaluate the initial state if no successor of it was improving.
        """
        batch_dir, _ = self._start_new_batch()
        self.initial_state = initial_state
        self.initial_state_run_dir = self._populate_run_dir(batch_dir, 0, initial_state)

    def evaluate_initial_state(self, evaluator_path, on_task_completed=None) -> EvaluationTask:
        """
        Evaluate the initial state that was stored with :meth:`remember_initial_state`
        earlier. If the state wasn't stored earlier, a SubmissionError is raised.
        """
        if self.initial_state_run_dir is None:
            raise SubmissionError("Could not evaluate initial state. Call "
            "'environment.remember_initial_state' before 'environment.evaluate_initial_state'.")
        init = Successor(self.initial_state,
                         "Evaluating successor state after search.")
        tasks = [EvaluationTask(init, 0, self.initial_state_run_dir)]
        job = EvaluationJob(f"{self.exp_name}-initial-state", evaluator_path, self.initial_state_run_dir.parent, tasks)
        self._run_job(job, on_task_completed)
        return job.tasks[0]

    def run(self, evaluator_path, batch, on_task_completed) -> list[EvaluationTask]:
        """
        Evaluate the given successors with the given evaluator. The evaluator is
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
        job = self._prepare_job(evaluator_path, batch)
        self._run_job(job, on_task_completed)
        return job.tasks


class LocalEnvironment(Environment):
    """
    This environment evaluates all successors sequentially on the local machine.

    See :class:`Environment` for inherited options.
    """
    def _run_job(self, job, on_task_completed):
        for task in job.tasks:
            if task.status == EvaluationTask.CANCELED:
                continue
            self._run_task(job.evaluator_path, task)
            ids_to_cancel = []
            if on_task_completed:
                ids_to_cancel = on_task_completed(task) or []
            for i in ids_to_cancel:
                if job.tasks[i].status == EvaluationTask.PENDING:
                    job.tasks[i].status = EvaluationTask.CANCELED

    def _run_task(self, evaluator_path: Path, task):
        cmd = [str(evaluator_path.absolute()), self.STATE_FILENAME]
        try:
            cwd = task.run_dir
            with (cwd/"run.log").open("w") as run_log, (cwd/"run.err").open("w") as run_err:
                process = subprocess.run(cmd, cwd=cwd, stdout=run_log, stderr=run_err)
                exit_code = process.returncode
        except subprocess.CalledProcessError as cpe:
            logging.warning(f"Failed to run evaluator in {task.run_dir}: " + format_called_process_error(cpe))

        _update_completed_task_status(task, exit_code)


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

        self.sbatch_template = resources.read_text(templates, "slurm-array-job.template")

    def _prepare_job(self, evaluator_path, batch):
        job = super()._prepare_job(evaluator_path, batch)

        run_dirs = [task.run_dir for task in job.tasks]
        # Give the NFS time to write the paths
        if not self._wait_for_filesystem(*run_dirs):
            logging.critical(
                f"One of the following paths is missing:\n"
                f"{pprint.pformat(run_dirs)}"
            )

        self._write_sbatch_file(job)
        return job

    def _run_job(self, job, on_task_completed):
        self._submit(job)
        pending_task_ids = set(range(len(job.tasks)))
        while pending_task_ids:
            time.sleep(self.POLLING_TIME_INTERVAL)
            self._update_status(job)
            pending_tasks_changed = True
            while pending_tasks_changed:
                pending_tasks_changed = False
                for task_id in set(pending_task_ids):
                    task = job.tasks[task_id]
                    if task.status != EvaluationTask.PENDING:
                        pending_task_ids.remove(task_id)
                        ids_to_cancel = on_task_completed(task)
                        if ids_to_cancel:
                            self._cancel(job, ids_to_cancel)
                        pending_tasks_changed = True
            if pending_task_ids:
                logging.info(
                    f"{len(pending_task_ids)} task"
                    f"{'s are' if len(pending_task_ids) > 1 else ' is'} still busy.")

    def _cancel(self, job, ids_to_cancel):
        slurm_ids = []
        for task_id in ids_to_cancel:
            task = job.tasks[task_id]
            if task.status != EvaluationTask.PENDING:
                continue
            slurm_ids.append(f"{job.slurm_id}_{task_id}")
            task.status = EvaluationTask.CANCELED

        if slurm_ids:
            try:
                subprocess.check_call(["scancel"] + slurm_ids)
            except subprocess.CalledProcessError as cpe:
                # Not being able to cancel jobs is not critical, we can wait until the tasks exit normally.
                logging.warning("Failed to cancel tasks: " + format_called_process_error(cpe))

    def _get_job_params(self, job):
        job_params = dict()
        job_params["name"] = job.name
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
        job_params["state_filename"] = self.STATE_FILENAME
        run_dirs = [str(task.run_dir) for task in job.tasks]
        job_params["run_dirs"] = " ".join(run_dirs)
        job_params["max_job_id"] = len(job.tasks) - 1
        job_params["evaluator_path"] = str(job.evaluator_path.absolute())
        return job_params

    def _submit(self, job):
        """
        Submits the current slurm array job and stores its ID in job.slurm_id.
        If the submission fails, a SubmissionError is raised.
        """
        submission_command = ["sbatch", "--export",
                              ",".join(self.export), job.sbatch_filename]
        try:
            output = subprocess.check_output(submission_command).decode()
        except subprocess.CalledProcessError as cpe:
            raise SubmissionError(format_called_process_error(cpe))

        match = re.match(r"Submitted batch job (\d*)", output)
        if not match:
            raise SubmissionError(
                "Something went wrong, no job ID printed after job submission.")

        job.slurm_id = match.group(1)
        logging.info(f"Submitted batch job {job.slurm_id}")

    def _wait_for_filesystem(self, *paths: [Path]):
        attempts = int(self.FILESYSTEM_TIME_LIMIT / self.FILESYSTEM_TIME_INTERVAL)
        for _ in range(attempts):
            paths = [path for path in paths if not path.exists()]
            if not paths:
                return True
            time.sleep(self.FILESYSTEM_TIME_INTERVAL)
        return False  # At least one path from paths does not exist

    def _write_sbatch_file(self, job):
        """
        Fills the template for job submission scripts with parameters from *job*
        and writes it in the batch directory. The location to the generated file
        is stored in job.sbatch_filename.
        """
        job_parameters = self._get_job_params(job)
        logging.debug(
            f"Parameters for sbatch template:\n{pprint.pformat(job_parameters)}")

        job.sbatch_filename = job.batch_dir/f"{job.name}.sbatch"
        content = self.sbatch_template.format(**job_parameters)
        Path(job.sbatch_filename).write_text(content)

    def _get_slurm_status(self, job):
        try:
            output = subprocess.check_output(
                ["sacct", "-j", str(job.slurm_id), "--format=jobid,state",
                 "--noheader", "--allocations"]).decode()
        except subprocess.CalledProcessError as cpe:
            raise PollingError(format_called_process_error(cpe))

        status_by_task_id = {}
        pattern = re.compile(r"(?P<job_id>\d+)_(?P<task_id>\d+)\+?\s+(?P<status>\w+)\+?")
        for line in output.splitlines():
            m = re.match(pattern, line)
            if m:
                assert m.group("job_id") == job.slurm_id
                task_id = int(m.group("task_id"))
                status = m.group("status")
                status_by_task_id[task_id] = status
            else:
                raise PollingError(
                    "Invalid format when querying `sacct` for task status.\n" +
                    output)
        return status_by_task_id

    def _update_status(self, job):
        status_by_task_id = self._get_slurm_status(job)
        for task in job.tasks:
            try:
                slurm_status = status_by_task_id[task.successor_id]
            except KeyError:
                raise PollingError(
                    f"Did not find status of slurm job {job.slurm_id}_{task.successor_id}.")

            if slurm_status in self.DONE_STATES:
                result_file = task.run_dir/"exit_code"
                self._wait_for_filesystem(result_file)
                try:
                    exit_code = _parse_exit_code(result_file)
                except IOError:
                    task.status = EvaluationTask.CRITICAL
                    task.error_msg = f"Missing exit code file '{str(result_file)}'"
                    continue
                _update_completed_task_status(task, exit_code)
            elif slurm_status in self.BUSY_STATES:
                task.status = EvaluationTask.PENDING
            else:
                task.status = EvaluationTask.CRITICAL
                task.error_msg = f"Unexpected Slurm status '{slurm_status}'"

            logging.debug(
                f"Task status of {job.slurm_id}_{task.successor_id} is {task.status} (slurm: {slurm_status})")

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
    exitcode = int(Path(result_file).read_text())
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
