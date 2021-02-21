

import subprocess

class Evaluator():
    def evaluate(self, state):
        pass

    def run_tasks(self, state):
        completed_process = subprocess.run(self.call_string_manager.call_string,
                                           text=True, capture_output=True, shell=True)
        return results
