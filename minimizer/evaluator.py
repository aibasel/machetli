import importlib
import logging
import sys

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


if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.critical(f"Expected two arguments to minimizer.evaluator but got {len(sys.argv)}.")
    evaluator_path = sys.argv[1]
    state_filename = sys.argv[2]
    state = st.read_and_unpickle_state(state_filename)
    if run_evaluator(evaluator_path, state):
        sys.exit(0)
    else:
        sys.exit(1)
