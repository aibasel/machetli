import logging
import os
import resource
import subprocess
import sys
import errno

from lab.calls.call import set_limit


class Run:
    """
    Stores a command and its optional time and memory limits.
    """

    def __init__(self, command, time_limit, memory_limit=None, log_output=None):
        self.command = command
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self.log_on_fail = True if log_output == "on_fail" else False
        self.log_always = True if log_output == "always" else False

    def __repr__(self):
        return f'Run(\"{" ".join([os.path.basename(part) for part in self.command])}\")'

    def start(self, state):
        """
        Formats the command according to *state* and executes it with *subprocess.Popen*. 
        Returns the 3-tuple (stdout, stderr, returncode) 
        with the values obtained from the executed command.
        """
        # These declarations are needed for the _prepare_call() function.
        time_limit = self.time_limit
        memory_limit = self.memory_limit

        def _prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                set_limit(resource.RLIMIT_AS, memory_limit *
                          1024 * 1024, hard_mem_limit)
            set_limit(resource.RLIMIT_CORE, 0, 0)

        formatted_command = [part.format(**state) for part in self.command]
        logging.debug(f"Formatted command:\n{formatted_command}")

        cwd = state["cwd"] if "cwd" in state else None

        try:
            process = subprocess.Popen(formatted_command,
                                       preexec_fn=_prepare_call,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True,
                                       cwd=cwd)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit('Error: Call "{}" failed. One of the files was not found.'.format(
                    ' '.join(formatted_command)))
            else:
                raise

        out_str, err_str = process.communicate()

        return (out_str, err_str, process.returncode)


class RunWithInputFile(Run):
    """
    Extends the *Run* class by adding the option of sending the content of a file to stdin,
    e.g., in a command like *path/to/./my_executable < my_input_file*.
    """

    def __init__(self, command, input_file, time_limit, memory_limit=None, log_output=None):
        super().__init__(command, time_limit=time_limit,
                         memory_limit=memory_limit, log_output=log_output)
        self.input_file = input_file

    def start(self, state):
        # These declarations are needed for the _prepare_call() function.
        time_limit = self.time_limit
        memory_limit = self.memory_limit

        def _prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                set_limit(resource.RLIMIT_AS, memory_limit *
                          1024 * 1024, hard_mem_limit)
            set_limit(resource.RLIMIT_CORE, 0, 0)

        formatted_command = [part.format(**state) for part in self.command]

        cwd = state["cwd"] if "cwd" in state else None

        try:
            process = subprocess.Popen(formatted_command,
                                       preexec_fn=_prepare_call,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       text=True,
                                       cwd=cwd)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit('Error: Call "{}" failed. One of the files was not found.'.format(
                    ' '.join(formatted_command)))
            else:
                raise

        f = open(self.input_file.format(**state), "r")
        input_text = f.read()
        f.close()

        out_str, err_str = process.communicate(input=input_text)

        return (out_str, err_str, process.returncode)


def run_all(state):
    """
    Starts all runs in *state["runs"]* and returns a dictionary where run outputs
    can be accessed the following ways: *results[run_name]["stdout]*, 
    *results[run_name]["stderr]* or *results[run_name]["returncode]*.
    """
    assert "runs" in state, "Could not find entry \"runs\" in state."
    results = {}
    for name, run in state["runs"].items():
        stdout, stderr, returncode = run.start(state)
        if run.log_always or run.log_on_fail and returncode != 0:
            if stdout:
                with open(os.path.join(state["cwd"], f"{name}.log"), "w") as logfile:
                    logfile.write(stdout)
            if stderr:
                with open(os.path.join(state["cwd"], f"{name}.err"), "w") as errfile:
                    errfile.write(stderr)
        results.update(
            {name: {"stdout": stdout, "stderr": stderr, "returncode": returncode}}
        )
    return results


def run_and_parse_all(state, parsers):
    """
    Executes *run_all(state)* and returns an updated version of the results
    dictionary containing the parsing results in place of the actual stdout
    and stderr outputs.
    """
    results = run_all(state)
    parsed_results = {}
    parsers = [parsers] if not isinstance(parsers, list) else parsers
    for name, result in results.items():
        parsed_results.update(
            {name: {"stdout": {}, "stderr": {},
                    "returncode": result["returncode"]}}
        )
        for parser in parsers:
            parsed_results[name]["stdout"].update(
                parser.parse(name, result["stdout"]))
            parsed_results[name]["stderr"].update(
                parser.parse(name, result["stderr"]))
    parsed_results["raw_results"] = results
    return parsed_results
