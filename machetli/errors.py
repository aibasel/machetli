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

class EvaluatorOutOfResourcesError(Exception):
    """
    Exception raised when an evaluator script exhausted its resource limits.
    """
    pass

class EvaluatorError(Exception):
    """
    Exception raised when an evaluator script did not exit with a valid return code.
    """
    pass

