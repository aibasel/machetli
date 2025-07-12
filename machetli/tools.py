"""
This module is derived from ``tools.py`` of Lab (<https://lab.readthedocs.io>).
Functions and classes that are not needed for this project were removed.
"""
from contextlib import contextmanager
import itertools
import logging
from pathlib import Path
import pickle
import re
import resource
import shutil
import subprocess
import sys
from typing import Union


DEFAULT_ENCODING = "utf-8"


# From https://docs.python.org/3/library/itertools.html#itertools-recipes
def batched(iterable, n):
    """Batch data into tuples of length n. The last batch may be shorter.

    :Example:

    .. code-block:: python

        batched('ABCDEFG', 3) # --> ABC DEF G


    """
    if n < 1:
        raise ValueError(f'batch size was {n=} but must be at least one')
    it = iter(iterable)
    while batch := tuple(itertools.islice(it, n)):
        yield batch


def get_script_path():
    """
    Get absolute path to main script, or the current working directory, if the
    Python session is interactive.
    """
    return Path(sys.argv[0]).absolute()


def get_script_dir():
    """
    Get absolute directory of the main script.
    """
    return get_script_path().parent


def get_python_executable():
    """
    Get path to the main Python executable.
    """
    return sys.executable or shutil.which("python")


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


def write_state(state, file_path: Union[Path, str]):
    """
    Use pickle to write a given state to disk.
    """
    Path(file_path).write_bytes(pickle.dumps(state))


def read_state(file_path: Union[Path, str]):
    """
    Use pickle to read a state from disk.
    """
    return pickle.loads(Path(file_path).read_bytes())


def parse(content, pattern, type=int):
    r"""
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

def _parse_limit(limit, suffixes, default):
    suffixes_str = "".join(suffixes)
    if limit is None:
        return None
    elif isinstance(limit, str):
        if m:= re.match(r"\s*(?P<value>\d+)\s*(?P<suffix>["
                        + suffixes_str.lower() + suffixes_str.upper() +
                        r"])?", limit):
            suffix = m.group("suffix")
            factor = suffixes.get(suffix.lower(), suffixes.get(suffix.upper(), default))
            value = int(m.group("value"))
            return value * factor
        else:
            supported_suffixes = ", ".join(suffixes_str)
            raise ValueError(f"We only support suffixes {{{supported_suffixes}}} "
                             f"but got `{limit}`")
    elif isinstance(limit, int):
        return limit * suffixes[default]
    else:
        raise ValueError(f"Unsupported type '{limit.type}'.")

def _time_limit_to_seconds(limit):
    return _parse_limit(limit, {"s": 1, "m": 60, "h": 60**2}, "s")

def _memory_limit_to_bytes(limit):
    return _parse_limit(limit, {"K": 1024, "M": 1024**2, "G": 1024**3}, "M")

def run(command, *, cpu_time_limit=None, memory_limit=None,
        core_dump_limit=0, input_filename=None,
        stdout_filename=None, stderr_filename=None, **kwargs):
    """
    This function is a wrapper for the `run` function of the Python `subprocess`
    module (see
    `subprocess <https://docs.python.org/3/library/subprocess.html>`_). It is
    meant as a convenience to ease common use cases of Machetli. A majority of
    the keyword parameters of `subprocess.run` are supported with the following
    changes:
    - `capture_output` is disallowed since we always capture output.
    - `input`, `stdout`, and `stderr` are replaced with `input_filename`,
      `stdout_filename`, and `stderr_filename`, respectively. They expect a
      `string` or `None` as input rather than a file or anything else. If they
      are set to `None`, the output is sent to `subprocess.PIPE` instead of
      written to files.

    :param command:
        A list of strings defining the command to execute. For details, see the
        Python module `subprocess <https://docs.python.org/3/library/subprocess.html>`_.

    :param cpu_time_limit:
        Time in seconds after which the command is terminated. Because states
        are evaluated in sequence in Machetli, it is important to use resource
        limits to make sure a command eventually terminates. There also is
        the parameter `timeout` from `subprocess.run` which is a wallclock
        time limit and generates an exception whereas we terminate after
        the program has been killed by the system. Instead of passing an
        integer, the time limit can also be passed as a string containing an
        integer and a suffix `s` (seconds), `m` (minutes), or `h` (hours).

    :param memory_limit:
        Memory limit in MiB to use for executing the command. Alternatively,
        a string containing an integer and a suffix `K` (KiB), `M` (MiB), or
        `G` (GiB).

    :param core_dump_limit:
        Limit in MiB of data written to disk in case the executed command
        crashes. By default we allow no core dump.

    :param input_filename:
        In case the process takes input on stdin, you can pass a path to a file
        here that will be piped to stdin of the process. With the default value
        of `None`, nothing is passed to stdin.

    :param stdout_filename:
        Redirect output to stdout to be written to the file of the given name.

    :param stderr_filename:
        Redirect output to stderr to be written to the file of the given name.

    """
    for keyword in ["input", "capture_output", "stdout", "stderr"]:
        if keyword in kwargs:
            logging.critical(f"Unsupported keyword parameter `{keyword}` of "
                             "function `tools.run`. See our documentation to "
                             "find out which keywords you can use instead of "
                             "these common `subprocess.run` keywords.")
    if "timeout" in kwargs and "cpu_time_limit" in kwargs:
        logging.info("Are you sure you want to set both a `timeout` and a "
                     "`cpu_time_limit` when calling `tools.run`? They might "
                     "end up in race conditions.")

    try:
        cpu_time_limit = _time_limit_to_seconds(cpu_time_limit)
    except ValueError as e:
        logging.critical("Unsupported format for parameter `cpu_time_limit` of "
                         f"function `tools.run`. {e}")

    try:
        memory_limit = _memory_limit_to_bytes(memory_limit)
    except ValueError as e:
        logging.critical("Unsupported format for parameter `memory_limit` of "
                         f"function `tools.run`. {e}")

    # This function is copied from lab.calls.call
    # (<https://github.com/aibasel/lab>).
    def _set_limit(kind, soft_limit, hard_limit):
        try:
            resource.setrlimit(kind, (soft_limit, hard_limit))
        except (OSError, ValueError) as err:
            logging.critical(
                f"Resource limit for {kind} could not be set to "
                f"[{soft_limit=}, {hard_limit=}] ({err})"
            )

    def _prepare_call():
        # When the soft CPU time limit is reached, SIGXCPU is emitted. Once we
        # reach the higher hard time limit, SIGILL is sent. Having some
        # padding between the two limits allows programs to handle SIGXCPU.
        if cpu_time_limit is not None:
            _set_limit(resource.RLIMIT_CPU, cpu_time_limit, cpu_time_limit + 5)
        if memory_limit is not None:
            _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
            _set_limit(resource.RLIMIT_AS, memory_limit, hard_mem_limit)
        _set_limit(resource.RLIMIT_CORE, core_dump_limit, core_dump_limit)

    @contextmanager
    def _open_or_pipe(filename, mode):
        if filename is None:
            yield subprocess.PIPE
        else:
            with filename.open(mode) as file:
                yield file

    encoding = kwargs.get("encoding")
    text_mode = encoding or kwargs.get("errors") or kwargs.get(
        "text") or kwargs.get("universal_newlines")
    if text_mode and encoding is None:
        encoding = "locale"

    def _read(path):
        return path.read_text(encoding) if text_mode else path.read_bytes()

    logging.debug(f"Command:\n{command}")

    input_path = Path(input_filename) if input_filename else None
    stdout_path = Path(stdout_filename) if stdout_filename else None
    stderr_path = Path(stderr_filename) if stderr_filename else None

    input_content= None
    if input_path is not None:
        input_content = _read(input_path)

    write_mode = "w" if text_mode else "wb"
    with _open_or_pipe(stdout_path, write_mode) as stdout, \
            _open_or_pipe(stderr_path, write_mode) as stderr:
        proc = subprocess.run(
            command, preexec_fn=_prepare_call, stdout=stdout,
            stderr=stderr, input=input_content, **kwargs)

    if stdout_path:
        proc.stdout = _read(stdout_path)
    if stderr_filename:
        proc.stderr = _read(stderr_path)

    return proc
