class Evaluator:
    """Interface for state evaluators.
    """
    parsers = None

    def evaluate(self, state):
        """Return ``True`` if *state* is accepted and ``False`` otherwise.
        Must be implemented in derived classes.
        """
        raise NotImplementedError()


class ParsingEvaluator(Evaluator):
    """Abstract :class:`Evaluator<minimizer.evaluator.Evaluator>` implementation
    for output and returncode parsing."""

    def evaluate(self, state):
        """Call :func:`run_and_parse_all(state, parsers)<minimizer.run.run_and_parse_all>`
        and return
        :meth:`self.interpret_results(results)<minimizer.evaluator.ParsingEvaluator.interpret_results>`."""
        with state_with_generated_pddl_files(state) as local_state:
            results = run_and_parse_all(local_state, self.parsers)
        return self.interpret_results(results)

    def interpret_results(self, results):
        """Return ``True`` or ``False``, depending on the content of
        the *results* dictionary.
        Must be implemented in derived classes.
        """
        raise NotImplementedError()
