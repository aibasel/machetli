Concepts
========

The core idea of the Minimizer stands on four pillars:

- At least one :ref:`run<run_concept>` to be executed. A run is basically a command-line string that starts a program.
- The problem :ref:`state<state_concept>`, which is simply a Python dictionary containing your runs and other useful data. You must define an initial state from where the search is started.
- At least one :ref:`successor generator<succ_gen_concept>`, which yields modified versions of the current state. Modifications to the state can be anything from manipulations of internal data structures to changes in program inputs.
- An :ref:`evaluator<evaluator_concept>`, which determines whether a given state has the properties you are looking for.

.. _run_concept:

Run Objects
-----------
To add more options to the program(s) you want to execute, the command-line string is embedded in a class called :class:`Run<minimizer.Run>`. It enables you to

- define a time limit in seconds for the executed program to finish (this parameter is required),
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
>>> with NamedTemporaryFile(mode="w+t") as temp:
...     file.write("Hello world!")
...     run2 = RunWithInputFile(command=["grep", "world"], input_file=temp.name time_limit=2)
...

.. _state_concept:

States
------
As mentioned above, a state is a Python dictionary. You can store in it anything you want behind any keyword, with a few exceptions:

- The keyword ``"runs"`` is reserved, because the Minimizer expects instances of the :class:`Run<minimizer.Run>` class to be stored in a sub-dictionary behind this keyword:

 .. code-block:: python

    # Assume run1, run2 and run3 have already been defined
    initial_state = {
        "runs": {
            "awesome_run": run1,
            "amazing_run": run2,
            "superb_run": run3
        }
    }

- When using one of the context managers from the :mod:`auxiliary module <minimizer.planning.auxiliary>`, the following keywords are reserved:

    - ``"pddl_task"``
    - ``"sas_task"``
    - ``"generated_pddl_domain_filename"``
    - ``"generated_pddl_problem_filename"``
    - ``"generated_sas_filename"``

.. _succ_gen_concept:

Successor Generators
--------------------
A successor generator is a class defining how successors of a :ref:`state<state_concept>` are constructed.
It should implement the :class:`SuccessorGenerator<minimizer.planning.generators.SuccessorGenerator>` class and especially the :meth:`get_successors(state)<minimizer.planning.generators.SuccessorGenerator.get_successors>` method, which is expected to return a `Python generator <https://docs.python.org/3/glossary.html#term-generator>`_ yielding successors of a state. Successor generators can be passed to a Minimizer search via their class name:

.. code-block:: python

    from minimizer.search import first_choice_hill_climbing
    # Other vital imports are omitted in this example

    # Assume initial_state, MyGenerator and SomeEvaluator have already been defined
    # MyGenerator and SomeEvaluator are class names
    result = first_choice_hill_climbing(initial_state, MyGenerator, SomeEvaluator)

If you want the search to be performed serially with multiple successors generators, you can pass a list of their class names in the order you want them to be used. The search result of each successor generator then becomes the initial state of the search with the following one:

.. code-block:: python

    result = first_choice_hill_climbing(initial_state, [Generator1, Generator2], SomeEvaluator)

The :mod:`minimizer.planning.generators` module provides a collection of readily available successors generators.

.. _evaluator_concept:

Evaluators
----------
