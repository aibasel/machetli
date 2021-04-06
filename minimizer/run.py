import resource
import subprocess
import sys
import errno

from lab.calls.call import set_limit
from minimizer.downward_lib import pddl_parser
from minimizer.sas_reader import sas_file_to_SASTask


class Run:
    """
    Stores a command and its optional time and memory limits.
    """
    def __init__(self, command, time_limit=None, memory_limit=None):
        self.command = command
        self.time_limit = time_limit
        self.memory_limit = memory_limit

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
                set_limit(resource.RLIMIT_AS, memory_limit * 1024 * 1024, hard_mem_limit)
            set_limit(resource.RLIMIT_CORE, 0, 0)

        formatted_command = [part.format(**state) for part in self.command]

        try:
            process = subprocess.Popen(formatted_command,
                                       preexec_fn=_prepare_call,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True)
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
    def __init__(self, command, input_file, time_limit=None, memory_limit=None):
        super().__init__(command, time_limit=time_limit, memory_limit=memory_limit)
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
                set_limit(resource.RLIMIT_AS, memory_limit * 1024 * 1024, hard_mem_limit)
            set_limit(resource.RLIMIT_CORE, 0, 0)

        formatted_command = [part.format(**state) for part in self.command]

        try:
            process = subprocess.Popen(formatted_command,
                                       preexec_fn=_prepare_call,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       text=True)
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
