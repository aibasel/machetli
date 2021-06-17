Concepts
========

The core idea of the Minimizer stands on four pillars:

- At least one *run* to be executed. A *run* is basically a command-line string that starts a program.
- The problem *state*, which is simply a Python dictionary containing your runs and other useful data. You must define an initial *state* from where the search is started.
- At least one *successor generator*, which yields modified versions of the current state. Modifications to the state can be anything from manipulations of internal data structures to changes in program inputs.
- An *evaluator*, which determines whether a given state has the properties you are looking for.

*Run* objects
---------------

To add more options to the program(s) you want to execute, the command-line string is embedded in a class called *Run*. It enables you to

- define a time limit in seconds for the executed program to finish (this parameter is even required),
- define a memory limit for the program,
- set a flag when you want output logs of the program to be written if it terminates on a non-zero exit code,
- set a flag when you want program outputs to always be written,
- pass the executed program a file whose content will be fed to the program as input.

Examples of defining a run:

>>> from minimizer.run import Run
>>> run1 = Run(command=["echo",  "Hello world!"], time_limit=2, memory_limit="100K", log_output="on_fail")
>>> # Example with input file:
>>> from minimizer.run import RunWithInputFile
>>> from tempfile import NamedTemporaryFile
>>> with NamedTemporaryFile(mode="w+t") as file:
...     file.write("Hello world!")
...     run2 = RunWithInputFile(command=["grep", "world"], input_file=file.name time_limit=2)
...

States
------

As mentioned above, a state is a Python dictionary. You can store in it anything you want behind any key value, with a few exceptions:

- The keyword ``"runs"`` is reserved, because the Minimizer expects instances of the *Run* class to be stored in a sub-dictionary behind this key:

 .. code-block:: python

    # Assume run1, run2 and run3 have already been defined above
    initial_state = {
        "runs": {
            "awesome_run": run1,
            "amazing_run": run2,
            "great_run": run3
        }
    }

- When using one of the context managers from the :ref:`auxiliary module <auxiliary>`, the following keywords are reserved:

    - ``"pddl_task"``
    - ``"sas_task"``
    - ``"generated_pddl_domain_filename"``
    - ``"generated_pddl_problem_filename"``
    - ``"generated_sas_filename"``