# import minimizer.state as state_util
from minimizer.pddl_writer import write_PDDL
from minimizer.sas_reader import write_SAS
from minimizer.downward_lib import timers
import subprocess
import os
from lab.calls.call import set_limit
import resource


class Evaluator:
    def evaluate(self, state):
        raise NotImplementedError()
