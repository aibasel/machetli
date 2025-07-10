Usage
=====

To use Machetli, you have to write two Python scripts:

* an evaluator script that checks if the behavior you are
  trying to isolate is still present in a state, and
* a search script that tells Machetli how to explore the
  space of instance modifications.

After installation, you can simply call ``machetli`` in a shell. Doing so
starts an interactive dialogue in which Machetli asks some questions about what
you would like to do. In the end, it automatically generates evaluator and
search scripts for your use case, which you can then immediately run to simplify
your problem. While it is convenient, this dialogue is limited to our most
common use cases and you may need more elaborate evaluator and search scripts.
In this case, you can either adapt the generated files or write your own
following the guidelines below.

.. _usage-evaluator:

Writing an evaluator script
---------------------------

The evaluator script is run for each state to check if the desired behavior (for
example, the bug we are trying to find) is still present after some
modifications of the instance. For technical reasons, it has to be implemented
in its own Python file. An evaluator is any script that takes the path to a
pickled state as its command line argument, and exits with
:attr:`EXIT_CODE_IMPROVING <machetli.evaluator.EXIT_CODE_IMPROVING>` if the
behavior is still present and
:attr:`EXIT_CODE_NOT_IMPROVING <machetli.evaluator.EXIT_CODE_NOT_IMPROVING>`
if it is not.

The module :mod:`machetli.evaluator` offers a covenience function
:meth:`machetli.evaluator.run_evaluator` that handles the input/output boiler
plate code. Using it, only a function that returns ``True`` or ``False`` is
required. Packages like :mod:`machetli.pddl` and :mod:`machetli.sas` offer
additional convenience (e.g., :meth:`machetli.pddl.run_evaluator`) where the
evaluation function is called with package-specific inputs. To write an
evaluator, we recommend using one of these convenience functions. Here is a
simple example:

.. code-block:: python
    :caption: evaluator.py
    :linenos:

    from machetli import pddl, tools

    def evaluate(domain, problem):
        command = ["./bugged-planner/plan", domain, problem]
        run = tools.Run(command, time_limit=20, memory_limit=3000)
        stdout, stderr, returncode = run.start()

        return "Wrong task encoding" in stdout

    if __name__ == "__main__":
        pddl.run_evaluator(evaluate)

Within the ``evaluate`` function you can run whatever code you want to test for
the desired behavior. This usually involves executing a program on the given
input and analyzing the behavior of that program, as in the example above. For
example, you could check the return code, the presence of a certain error or log
messages in the output, or compare the result against a reference program.

The module :mod:`machetli.tools` contains useful methods to make running and
analyzing a program easier.

.. admonition:: Caveats

    There are some pitfalls to look out for when writing an evaluator.

    * Unlike in `Lab <https://lab.readthedocs.io>`_, (currently) **Machetli does
      not compile your project** at a specified revision when it is executed. It
      expects you to do this in advance and specify the compiled executable to
      be used.
    * When running programs within an evaluator, we strongly recommend to **use
      resource bounds** on time and memory to prevent the process getting stuck
      for some of the modified instances. Machetli doesn't enforce any
      additional resource limits, so it is up to you to ensure that the
      processes terminate. If you cannot determine if the behavior is still
      present or not because of resource limits, exit the evaluator with exit code
      :attr:`EXIT_CODE_RESOURCE_LIMIT <machetli.evaluator.EXIT_CODE_RESOURCE_LIMIT>`.
    * Make sure your evaluator **specifically tests for the behavior you are
      interested in**. If the test is too broad unrelated bugs could be mixed up
      with the one you are trying to find. For example, if you are looking for a
      bug where an exception is thrown, look for the output of that exception
      in the program's output rather than just looking at the exit code.



Writing the search script
-------------------------

Once you have an evaluator that can check if the behavior you are interested in
is present in a state, it is time to write a search script. This script should
do the following:

1. Set up the initial state of the search. The packages :mod:`machetli.pddl` and
   :mod:`machetli.sas` provide specialized methods for this purpose.

   .. code-block:: python

       initial_state = pddl.generate_initial_state("large-domain.pddl", "large-problem.pddl")

2. Select which modifications the search should try. Use some or all of the
   successor generators of the package you are working with
   (:mod:`machetli.pddl` or :mod:`machetli.sas`). These have to match the
   initial state, i.e., if you set up your initial state as a PDDL instance, you
   cannot use successor generators from the package :mod:`machetli.sas`.

   .. code-block:: python

       successor_generators = [pddl.RemoveActions(), pddl.RemoveObjects(), pddl.ReplaceLiteralsWithTruth()]

3. Specify the location of the evalutor script.

   .. code-block:: python

       evaluator_filename = "./evaluator.py"

4. Start the search by calling :meth:`machetli.search<machetli.search>` with the
   information collected in steps 1-3.

   .. code-block:: python

       result = search(initial_state, successor_generators, evaluator_filename)

5. Store the resulting instance. The packages :mod:`machetli.pddl` and
   :mod:`machetli.sas` provide specialized methods for this purpose.

   .. code-block:: python

       pddl.write_files(result, "small-domain.pddl", "small-problem.pddl")

Putting everything together, here is the complete example:

.. code-block:: python
    :linenos:

    from machetli import pddl, search

    initial_state = pddl.generate_initial_state("large-domain.pddl", "large-problem.pddl")
    successor_generators = [pddl.RemoveActions(), pddl.RemoveObjects(), pddl.ReplaceLiteralsWithTruth()]
    evaluator_filename = "./evaluator.py"
    result = search(initial_state, successor_generators, evaluator_filename)
    pddl.write_files(result, "small-domain.pddl", "small-problem.pddl")


Running the search on a grid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Machetli can parallelize the work of looking for a better instance when it is
executed on a grid. To do so, pass an :mod:`Environment<machetli.environments>` to
the search function. By default, Machetli uses a
:class:`LocalEnvironment<machetli.environments.LocalEnvironment>` which executes
everything in sequenceon the local machine. If you use a
:class:`SlurmEnvironment<machetli.environments.SlurmEnvironment>` instead, the
evaluation of generated states will be scheduled in batches on a grid running
`Slurm <https://slurm.schedmd.com/overview.html>`_.

.. note:: Uni Basel users can use the specialized class :class:`BaselSlurmEnvironment<machetli.environments.BaselSlurmEnvironment>` instead.

.. code-block:: python
    :linenos:

    from machetli import environments

    result = search(initial_state, successor_generators, evaluator_filename, BaselSlurmEnvironment())

The main thread will keep running on login node of the grid and interact with
the grid engine to submit jobs for evaluating states. We recommend running it in
a ``screen`` environment.


Examples
--------

An `interactive demo of Machetli <https://tinyurl.com/machetli-demo>`_ is
available as a Jupyter notebook on Google Colab. You can find additional
examples in the directory `examples
<https://github.com/aibasel/machetli/tree/main/examples>`_.
