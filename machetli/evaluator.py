import importlib
import logging
import platform
import sys

from machetli.tools import read_state

# https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path/50395128#50395128
def _import_evaluator(module_name, evaluator_path):
    spec = importlib.util.spec_from_file_location(module_name, evaluator_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module 
    spec.loader.exec_module(module)
    return module


def is_evaluator_successful(evaluator_path, state):
    module = _import_evaluator("custom_evaluator", evaluator_path)
    return module.evaluate(state)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        logging.critical(f"Expected two arguments to machetli.evaluator but got {len(sys.argv)}.")
    evaluator_path = sys.argv[1]
    state_filename = sys.argv[2]
    logging.info(f"Running evaluator '{evaluator_path}' for state '{state_filename}' on node: {platform.node()}.")

    state = read_state(state_filename, 5, 2)
    if is_evaluator_successful(evaluator_path, state):
        sys.exit(0)
    else:
        sys.exit(1)
