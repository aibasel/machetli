import resource
from lab.calls.call import set_limit


class Run:
    def __init__(self, command, domain_file=None, problem_file=None, input_file=None, time_limit=None, memory_limit=None):
        from minimizer.downward_lib import pddl_parser
        from minimizer.sas_reader import sas_file_to_SASTask
        self.command = command
        self.domain_file = domain_file
        self.problem_file = problem_file
        self.input_file = input_file
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self.pddl_task = pddl_parser.open(
            domain_filename=domain_file, task_filename=problem_file) if domain_file and problem_file else None
        self.sas_task = sas_file_to_SASTask(input_file) if input_file else None

    def start(self):
        """
        Executes the command using subprocess.Popen. 
        Returns the 3-tuple (stdout, stderr, returncode) 
        with the values obtained from the executed command.
        """
        def get_bytes(limit):
            return None if limit is None else int(limit * 1024)

        time_limit = self.time_limit
        memory_limit = self.memory_limit
        def prepare_call():
            # When the soft time limit is reached, SIGXCPU is emitted. Once we
            # reach the higher hard time limit, SIGKILL is sent. Having some
            # padding between the two limits allows programs to handle SIGXCPU.
            if time_limit is not None:
                set_limit(resource.RLIMIT_CPU, time_limit, time_limit + 5)
            if memory_limit is not None:
                _, hard_mem_limit = resource.getrlimit(resource.RLIMIT_AS)
                # Convert memory from MiB to Bytes.
                set_limit(
                    resource.RLIMIT_AS, memory_limit * 1024 * 1024, hard_mem_limit
                )
            set_limit(resource.RLIMIT_CORE, 0, 0)

        input_content = self._get_input_content()

        try:
            process = subprocess.Popen(args,
                                       preexec_fn=prepare_call,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE if input_content else None,
                                       text=True)
        except OSError as err:
            if err.errno == errno.ENOENT:
                sys.exit(f'Error: Call {name} failed. "{args[0]}" not found.')
            else:
                raise
        except subprocess.SubprocessError as sErr:
            raise

        out_str, err_str = process.communicate(input=input_content)

        return (out_str, err_str, process.returncode)

    def _get_input_content(self):
        if not self.input_file:
            return None
        else:
            f = open(self.input_file, "r")
            input_content = f.read()
            f.close()
            return input_content