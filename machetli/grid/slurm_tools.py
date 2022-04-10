import logging
import os
import pkgutil
import re
import subprocess

from machetli import tools

TEMPLATE_FILE = "slurm-array-job.template"


def parse_exit_code(result_file):
    with open(result_file, "r") as rf:
        exitcode = int(rf.read())
    return exitcode


def fill_template(**parameters):
    template = tools.get_string(pkgutil.get_data(
        "machetli", os.path.join("grid", TEMPLATE_FILE)))
    return template.format(**parameters)


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
                "Something went wrong while trying to send the "
                "notification email.")
    return


def check_for_whitespace(path):
    assert not re.search(r"\s+", path), \
        "The script path must not contain any whitespace characters."
