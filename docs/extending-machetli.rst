.. _extending-machetli:

==================
Extending Machetli
==================

Machetli comes with some existing methods to simplify PDDL and SAS\ :sup:`+`
tasks. If those are not sufficient for your case or if your instances are in a
different format, you can easily extend Machetli.

.. _extending-machetli-successor-generator:

Adding a new successor generator
--------------------------------

A successor generator implements a specific simplification step in an instance.
You can create custom successor generators be inheriting from the class
:class:`SuccessorGenerator <machetli.successors.SuccessorGenerator>` and
implementing the method
:meth:`get_successors(state)<machetli.successors.SuccessorGenerator.get_successors>`.
Your implementation should yield objects of the class
:class:`Successor <machetli.successors.Successor>` that contain a modified
state and a message that will be printed if the search follows this successor.

Example: removing goal conditions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As an example, consider a successor generator that simplifies the goal of an
SAS\ :sup:`+` task (this successor generator actually is already implemented but
for this example we pretend it isn't). We start by importing the necessary
classes and constants.

.. code-block:: python
    :linenos:

    import copy
    import random

    from machetli.successors import Successor, SuccessorGenerator
    from machetli.sas.constants import KEY_IN_STATE


We then derive a new class from :class:`SuccessorGenerator <machetli.successors.SuccessorGenerator>`
and implement the method :meth:`get_successors<machetli.successors.SuccessorGenerator.get_successors>`.
Within the state we can access the parsed SAS\ :sup:`+` task with the constant ``KEY_IN_STATE``.

.. code-block:: python
    :linenos:
    :lineno-start: 7

    class RemoveGoals(SuccessorGenerator):
        def get_successors(self, state):
            task = state[KEY_IN_STATE]
            # ...

The task's goal is a list of variable-value pairs and we can remove any entry to
simplify the task. We want to create one successor for each such modification,
so we loop over the goals to remove. (Even though this is not strictly
necessary, we randomize the order to avoid a bias for variables with lower
index.) In each case, we create a copy of the state and delete the respective
goal from the copy. Finally, we ``yield`` a successor containing the child state
and a message explaining the modificaiton.

.. code-block:: python
    :linenos:
    :lineno-start: 10
    
            # ...
            num_goals = len(task.goal.pairs)
            for goal_id in random.sample(range(num_goals), num_goals):
                child_state = copy.deepcopy(state)
                del child_state[KEY_IN_STATE].goal.pairs[goal_id]
                yield Successor(child_state, f"Removed a goal. Remaining goals: {num_goals - 1}")

Using ``yield`` here (compared to returning a list of all successors) avoids
creating all successors before evaluating the first one. We strongly recommend
this in cases where a successor generator can create many successors. The
message passed to the successor will be displayed on the command line if this
successor is picked by the search (i.e., if it is the first one that still
exhibits the behavior the user is trying to isolate).

.. _extending-machetli-file-type:

Supporting a new file type
--------------------------

Machetli is not limited to PDDL and SAS\ :sup:`+` files. The main work in
supporting a new file type is writing the successor generators as discussed
above. In addition, you should provide functions to parse your instances and
write them back to disk. As an example, consider the methods provided in the
package :mod:`machetli.pddl`:

* :meth:`generate_initial_state<machetli.pddl.generate_initial_state>` parses a
  PDDL file form the disk and returns a state containing the parsed data.
  Machetli states are dictionaries and you can store parsed data under any key
  you want as long as the successor generators know about and use the same key.
  In the existing packages, we use a constant ``KEY_IN_STATE`` for this
  purpose.
* :meth:`write_files<machetli.pddl.write_files>` writes the parsed data to disk.
  This is used to store the PDDL input files for each state and at the end of the
  search to store the result.

While these two are technically sufficient, we recommend to also provide a function
to simplify writing evaluators. In package :mod:`machetli.pddl`, this is:

* :meth:`run_evaluator<machetli.pddl.run_evaluator>` loads the state given to
  the evaluator script, writes the PDDL files to disk, and
  then calls a PDDL specific evaluation function. We also recommend to have this
  function fall back to generating a state directly from your file type (a PDDL
  instance in this case) to make testing the evaluator easier.


Example: finding bugs in LaTeX documents
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the following example, we combine what we discussed in the previous sections
to create rudimentary support for LaTeX documents.

We start with functions to read and write LaTeX files. For the sake of a simpler
example, we just store the raw text in the LaTeX files. A better implementation
would parse the document and store the parsed data instead, so successor
generators can directly access entities like sections, included packages, etc.

.. code-block:: python
    :linenos:

    def generate_initial_state(filename):
        with open(filename) as f:
            content = f.read()
        return {"latex" : content}

    def write_files(state, filename):
        with open(filename, "w") as f:
            f.write(state["latex"])


For added convenience, we implement a ``run_successor`` function:

.. code-block:: python
    :linenos:
    :lineno-start: 9

    import logging
    from pickle import PickleError
    import sys
    from machetli import tools, evaluator

    def run_evaluator(evaluate):
        if len(sys.argv) == 2:
            filename = sys.argv[1]
            try:
                state = tools.read_state(filename)
            except PickleError:
                state = generate_initial_state(filename)
        else:
            logging.critical("Call evaluator with state or tex file.")
            sys.exit(evaluator.EXIT_CODE_CRITICAL)

        write_files(state, "file.tex")
        if evaluate("file.tex"):
            sys.exit(evaluator.EXIT_CODE_IMPROVING)
        else:
            sys.exit(evaluator.EXIT_CODE_NOT_IMPROVING)


Finally, we add a simple successor generator that removes a single line from the
document:

.. code-block:: python
    :linenos:
    :lineno-start: 30

    from machetli.successors import Successor, SuccessorGenerator

    class RemoveLine(SuccessorGenerator):
        def get_successors(self, state):
            lines = state["latex"].splitlines()
            for i in range(len(lines)):
                child_lines = list(lines)
                del child_lines[i]
                child_state = {"latex": "\n".join(child_lines)}
                yield Successor(child_state, f"Removed one of {len(lines)} lines.")
