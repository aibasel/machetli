class SubmissionError(Exception):
    """
    Exception raised when submitting a batch of successors fails.
    """
    pass

class PollingError(Exception):
    """
    Exception raised when querying the status of a submitted successor evaluation fails.
    """
    pass

def format_called_process_error(cpe):
    return f"""Submission command: {cpe.cmd}
Returncode: {cpe.returncode}
Output: {cpe.output}
Captured stdout:
----------------
{cpe.stdout}

Captured stderr:
----------------
{cpe.stderr}
"""
