
from lab.experiment import Experiment
import subprocess
from lab.tools import Properties
import copy


class Evaluator():
    def evaluate(self, state):
        pass

    def run_tasks(self, state, parsers):
        if not isinstance(parsers, list):
            parsers = [parsers]
        results = {}
        props = Properties()
        for call in state["call_strings"]:
            output = subprocess.run(state["call_strings"][call], text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
            with open("run.log", "w") as f:
                f.write(output)

            results[call] = {}
            for parser in parsers:
                parser.parse()
                results[call].update(copy.deepcopy(parser.props))

        subprocess.run(["rm", "properties", "run.log", "sas_plan"])
        return results
