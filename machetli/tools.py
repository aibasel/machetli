"""
This module is derived from ``tools.py`` of Lab (<https://lab.readthedocs.io>).
Functions and classes that are not needed for this project were removed.
"""
import errno
import logging
import os
import pickle
import pprint
import random
import re
import resource
import subprocess
import sys
import time


DEFAULT_ENCODING = "utf-8"


def get_string(s):
    """
    Decode a byte string.
    """
    if isinstance(s, bytes):
        return s.decode(DEFAULT_ENCODING)
    else:
        raise ValueError("tools.get_string() only accepts byte strings")


def get_script_path():
    """
    Get absolute path to main script.
    """
    return os.path.abspath(sys.argv[0])


def get_python_executable():
    """
    Get path to the main Python executable.
    """
    return sys.executable or "python"


def configure_logging(level=logging.INFO):
    """
    Set up internal loggers to only print messages at least as important as the
    given log level.Warnings and error messages will be printed on
    stderr, and critical messages will terminate the program.
    All messages will be prefixed with the current time.
    """
    # Python adds a default handler if some log is written before this
    # function is called. We therefore remove all handlers that have
    # been added automatically.
    root_logger = logging.getLogger("")
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    class ErrorAbortHandler(logging.StreamHandler):
        """
        Logging handler that exits when a critical error is encountered.
        """

        def emit(self, record):
            logging.StreamHandler.emit(self, record)
            if record.levelno >= logging.CRITICAL:
                sys.exit("aborting")

    class StdoutFilter(logging.Filter):
        def filter(self, record):
            return record.levelno <= logging.WARNING

    class StderrFilter(logging.Filter):
        def filter(self, record):
            return record.levelno > logging.WARNING

    formatter = logging.Formatter("%(asctime)-s %(levelname)-8s %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(StdoutFilter())

    stderr_handler = ErrorAbortHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.addFilter(StderrFilter())

    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)
    root_logger.setLevel(level)

# TODO: only used by a deprecated parser function. will be removed.
def make_list(value):
    """
    Turn tuples, sets, lists and single objects into lists of objects.

    .. note:: Deprecated (might be removed soon)
    """
    if value is None:
        return []
    elif isinstance(value, list):
        return value[:]
    elif isinstance(value, (tuple, set)):
        return list(value)
    else:
        return [value]


def makedirs(path):
    """
    os.makedirs() variant that doesn't complain if the path already exists.
    """
    try:
        os.makedirs(path)
    except OSError:
        # Directory probably already exists.
        pass


def write_state(state, file_path):
    """
    Use pickle to write a given state to disk.
    """
    with open(file_path, "wb") as state_file:
        pickle.dump(state, state_file)


def read_state(file_path, wait_time, repetitions):
    """
    Use pickle to read a state from disk. We expect this operation to occur on a
    network file system that might take some time to synchronize, so we retry
    the read operation multiple times if it fails, waiting a random amount
    of time before each attempt (between 0 and *wait_time* seconds).
    """
    for _ in range(repetitions):
        time.sleep(wait_time * random.random())
        if os.path.exists(file_path):
            with open(file_path, "rb") as state_file:
                return pickle.load(state_file)
    else:
        logging.critical(f"Could not find file '{file_path}' after {repetitions} attempts.")


class SubmissionError(Exception):
    """
    Exception thrown when submitting a slurm job on the grid fails.

    .. note:: Deprecated (might be removed soon)
    """
    def __init__(self, cpe):
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
        logging.warning(f"The following batch submission failed but is "
                        f"ignored: {self}")

    def warn_abort(self):
        logging.error(
            f"Task order cannot be kept because the following batch "
            f"submission failed: {self} Aborting search.")


class TaskError(Exception):
    """
    Exception thrown when a slurm job on the grid enters a critical state.

    .. note:: Deprecated (might be removed soon)
    """
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
            f"Some tasks from job {job['id']} entered a critical "
            f"state but the search is continued.")

    def remove_tasks_after_first_critical(self, job):
        """
        Remove all tasks from job after the first one that entered a
        critical state.
        """
        first_failed = self.indices_critical[0]
        job["tasks"] = job["tasks"][:first_failed]
        if not job["tasks"]:
            logging.error("Since the first task failed, the order "
                          "cannot be kept. Aborting search.")
        else:
            logging.warning(
                f"At least one task from job {job['id']} entered a "
                f"critical state: {self} The tasks before the first "
                f"critical one are still considered.")


class PollingError(Exception):
    """
    Exception thrown when querying the status of a slurm job on the grid fails.

    .. note:: Deprecated (might be removed soon)
    """
    def __init__(self, job_id):
        self.job_id = job_id

    def warn_abort(self):
        logging.error(f"Polling job {self.job_id} caused an error. "
                      f"Aborting search.")

# This function is copied from lab.calls.call (<https://lab.readthedocs.org>).
def _set_limit(kind, soft_limit, hard_limit):
    try:
        resource.setrlimit(kind, (soft_limit, hard_limit))
    except (OSError, ValueError) as err:
        logging.critical(
            f"Resource limit for {kind} could not be set to "
            f"[{soft_limit}, {hard_limit}] ({err})"
        )


def parse(content, pattern, type=int):
    """
    Look for matches of *pattern* in *content*. If any matches are found, the
    first group present in the regular expression is cast as *type* and
    returned.

    :Example:

    .. code-block:: python

        content = '''
        Runtime: 23.5s
        Heuristic value: 42
        Search successful
        '''
        t = parse(content, r"Runtime: (\.+)s", float)
        h = parse(content, r"Heuristic value: (\d+)", int)


    """
    if type == bool:
        logging.warning(
            "Casting any non-empty string to boolean will always "
            "evaluate to true. Are you sure you want to use type=bool?"
        )

    regex = re.compile(pattern)
    match = regex.search(content)
    if match:
        try:
            value = match.group(1)
        except IndexError:
            logging.critical(f"Regular expression '{regex}' has no groups.")
        else:
            return type(value)
    else:
        logging.debug(f"Failed to find pattern '{regex}'.")


class Run:
    """
    Define an executable command with time and memory limits.

    :param command: is a list of strings defining the command to execute. For details, see
        the Python module
        `subprocess <https://docs.python.org/3/library/subprocess.html>`_.

    :param time_limit: time in seconds after which the command is terminated.
        Because states are evaluated in sequence in Machetli, it is important
        to use resource limits to make sure a command eventually terminates.

    :param memory_limit: memory limit in MiB to use for executing the command.

    :param log_output:
        the method :meth:`start` will return whatever the command writes to
        stdout and stderr as strings. However, this log output will not be
        written to the main log or to disk, unless you specify it otherwise in
        this option. Use the *log_output* option ``"on_fail"`` if you want log
        files to be written when *command* terminates on a non-zero exit code or
        use the option ``"always"`` if you want them always to be written.

        .. note:: This option currently does not work and is ignored.

    :param input_file:
        in case the process takes input on stdin, you can pass a path to a file
        here that will be piped to stdin of the process. With the default value
        of `None`, nothing is passed to stdin.

    """

    def __init__(self, command, time_limit=1800, memory_limit=None,
                 log_output=None, input_file=None):
        self.command = command
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self.log_on_fail = log_output == "on_fail"
        self.log_always = log_output == "always"
        self.input_file = input_file

    def __repr__(self):
        cmd = " ".join([os.path.basename(part) for part in self.command])
        if self.input_file:
            cmd += f" < {self.input_file}"
        return f'Run(\"{cmd}\")'

    def start(self):
        """
        Run the command with the given resource limits
        
        :returns: the 3-tuple (stdout, stderr, returncode) with the values
            obtained from the executed command.
        """
        # These declarations are needed for the _prepare_call() function.
        time_limit = self.time_limit
        memory_limit = self.memory_limit

        def _prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                _set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                _set_limit(resource.RLIMIT_AS, memory_limit *
                           1024 * 1024, hard_mem_limit)
            _set_limit(resource.RLIMIT_CORE, 0, 0)

        logging.debug(f"Command:\n{self.command}")

        stdin = subprocess.PIPE if self.input_file else None
        process = subprocess.Popen(self.command,
                                   preexec_fn=_prepare_call,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=stdin,
                                   text=True)
        input_text = None
        if self.input_file:
            with open(self.input_file, "r") as file:
                input_text = file.read()

        out_str, err_str = process.communicate(input=input_text)

        # TODO: The following block stems from *run_all* and we might want to
        #  reuse some of its logic.
        # if run.log_always or run.log_on_fail and returncode != 0:
        #     cwd = state["cwd"] if "cwd" in state else os.path.dirname(
        #         get_script_path())
        #     if stdout:
        #         with open(os.path.join(cwd, f"{name}.log"), "w") as logfile:
        #             logfile.write(stdout)
        #     if stderr:
        #         with open(os.path.join(cwd, f"{name}.err"), "w") as errfile:
        #             errfile.write(stderr)

        return out_str, err_str, process.returncode
