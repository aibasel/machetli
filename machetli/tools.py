"""
This file is derived from ``tools.py`` of Lab (<https://lab.readthedocs.io>).
Functions and classes that are not needed for this project were removed.
"""
import logging
import os
import pickle
import pprint
import random
import sys
import time


DEFAULT_ENCODING = "utf-8"


def get_string(s):
    if isinstance(s, bytes):
        return s.decode(DEFAULT_ENCODING)
    else:
        raise ValueError("tools.get_string() only accepts byte strings")


def get_script_path():
    """Get absolute path to main script."""
    return os.path.abspath(sys.argv[0])


def get_python_executable():
    return sys.executable or "python"


def configure_logging(level=logging.INFO):
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
    with open(file_path, "wb") as state_file:
        pickle.dump(state, state_file)


def read_state(file_path, wait_time, repetitions):
    for _ in range(repetitions):
        time.sleep(wait_time * random.random())
        if os.path.exists(file_path):
            with open(file_path, "rb") as state_file:
                return pickle.load(state_file)
    else:
        logging.critical(f"Could not find file '{filename}' after {repetitions} attempts.")


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
        logging.warning(f"The following batch submission failed but is "
                        f"ignored: {self}")

    def warn_abort(self):
        logging.warning(
            f"Task order cannot be kept because the following batch "
            f"submission failed: {self} Aborting search.")


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
            logging.warning("Since the first task failed, the order "
                            "cannot be kept. Aborting search.")
        else:
            logging.warning(
                f"At least one task from job {job['id']} entered a "
                f"critical state: {self} The tasks before the first "
                f"critical one are still considered.")


class PollingError(Exception):
    def __init__(self, job_id):
        self.job_id = job_id

    def warn_abort(self):
        logging.error(f"Polling job {self.job_id} caused an error. "
                      f"Aborting search.")

