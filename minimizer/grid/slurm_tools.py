import argparse
import logging
import os
import pickle
import pkgutil
import platform
import re
import subprocess
import sys
import time

from minimizer.grid import slurm_tools
from lab import tools

TEMPLATE_FILE = "slurm-array-job.template"
DEFAULT_ARRAY_SIZE = 200


def pickle_and_dump_state(state, file_path):
    with open(file_path, "wb") as dump_file:
        pickle.dump(state, dump_file)


def read_and_unpickle_state(file_path):
    with open(file_path, "rb") as dump_file:
        return pickle.load(dump_file)


def parse_result(result_file):
    rf = open(result_file, "r")
    match = re.match(
        r"The evaluation finished with exit code (\d+)", rf.read())
    rf.close()
    exitcode = int(match.group(1))
    result = True if exitcode == 0 else False
    return result


def get_next_batch(successor_generator, batch_size):
    while True:
        batch = []
        for _ in range(batch_size):
            try:
                next_state = next(successor_generator)
                batch.append(next_state)
            except StopIteration:  # generator exhausted, exit function
                if batch:
                    yield batch
                return
        else:
            yield batch


def fill_template(**parameters):
    template = tools.get_string(pkgutil.get_data(
        "minimizer", os.path.join("grid", TEMPLATE_FILE)))
    return template % parameters


def launch_email_job(environment):
    if environment.email:
        try:
            subprocess.run(["sbatch",
                            "--job-name='Search terminated'",
                            "--mail-type=BEGIN",
                            f"--mail-user={environment.email}"],
                           input=b"#! /bin/bash\n")
        except:
            logging.warning(
                "Something went wrong while trying to send the notification email.")
    return


def check_for_whitespace(path):
    assert not re.search(
        r"\s+", path), "The script path must not contain any whitespace characters."
