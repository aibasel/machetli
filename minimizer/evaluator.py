import importlib
import logging
import random
import sys
import time

from minimizer.grid import slurm_tools as st

# https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path/50395128#50395128
def import_evaluator(module_name, evaluator_path):
    spec = importlib.util.spec_from_file_location(module_name, evaluator_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module 
    spec.loader.exec_module(module)
    return module

def run_evaluator(evaluator_path, state):
    module = import_evaluator("custom_evaluator", evaluator_path)
    return module.evaluate(state)


def wait_for_file(filename, wait_time=5, repetitions=10):
        for _ in range(repetitions):
            time.sleep(wait_time * random.random())
            if os.path.exists(filename):
                break
        else:
            logging.critical(f"Could not find file '{filename}' after {repetitions} attempts.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.critical(f"Expected two arguments to minimizer.evaluator but got {len(sys.argv)}.")
    evaluator_path = sys.argv[1]
    state_filename = sys.argv[2]
    wait_for_file(state_filename)
    state = st.read_and_unpickle_state(state_filename)
    logging.info(f"Node: {platform.node()}")
    if run_evaluator(evaluator_path, state):
        sys.exit(0)
    else:
        sys.exit(1)
