Tutorial
========

.. _grid_335:

PDDL Grid Example
-----------------
Below, you see an example application of the minimizer on a Slurm computing grid. The script is excessively commented to provide insight into as many details as possible. If you have the two required environment variables set (``PYTHON_3_7`` and ``DOWNWARD_REPO`` (at commit 09ccef5fd)), you can execute the script (on a Slurm computing node) and see the minimizer in action.

For an example on your local machine, jump to the :ref:`next example <local_335>`.

.. literalinclude:: ../examples/issue335_PDDL/grid_test.py
   :language: python
   :caption:
   :linenos:

.. _local_335:

PDDL Local Example
------------------
The next script shows how to execute the same minimizer search on your local machine. Notice how the only difference (apart from the missing comments) is the different environment defined in line 67.

.. literalinclude:: ../examples/issue335_PDDL/local_test.py
   :language: python
   :caption:
   :emphasize-lines: 67
   :linenos:

.. _local_sas:

SAS\ :sup:`+` Local Example
---------------------------
The following script shows an example of how to use the minimizer when you want to minimize a SAS\ :sup:`+` task directly. It is only lightly commented due to its similarity with the :ref:`first example <grid_335>`. Some lines are highlighted to point out the differences to the PDDL examples. 

.. literalinclude:: ../examples/segmentation_fault_SAS+/local_test.py
   :language: python
   :caption:
   :emphasize-lines: 13, 40-43, 45-48, 64-66, 74, 78
   :linenos: