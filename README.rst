.. image:: docs/machetli.svg
   :width: 20 %
   :align: right
   :alt:

Machetli
========

**Machetli** is a Python package for reproducing characteristics of a program
(such as bugs) with modified instances. It is meant to be helpful for debugging
complex programs and narrowing down where specific behaviors are caused.

Currently, Machetli handles instances for automated planners, specified either
in PDDL or in the SAS\ :sup:`+` format used by `Fast Downward
<https://www.fast-downward.org>`__ but adding support for other file formats is
easy.


Installation
------------

Machetli requires Python 3.7+ and can be installed with ``pip``.

.. code-block:: bash

    pip install machetli

If you want to avoid changes to your system-wide Python installation you can
`install Machetli in a virtual Python environment
<https://machetli.readthedocs.io/en/latest/installation.html>`_.


Usage
-----

The easiest way to get started is by calling ``machetli`` from the command line.
Machetli guides you through the process of setting up scripts for its most
common use case. If your use case is different you can find an
`interactive demo of Machetli <https://tinyurl.com/machetli-demo>`_ as a Jupyter
notebook on Google Colab. You can find additional examples in the directory
`examples <https://github.com/aibasel/machetli/tree/main/examples>`_.

For a more detailed description, please refer to the `documentation
<https://machetli.readthedocs.io/en/latest/usage.html>`_.


Support
-------

* Documentation: https://machetli.readthedocs.io
* Issue tracker: https://github.com/aibasel/machetli/issues
* Code: https://github.com/aibasel/machetli


License
-------

Machetli is licensed under GPL3. We use code from `Fast Downward
<https://github.com/aibasel/downward>`__ and `Lab <https://github
.com/aibasel/lab>`_ under GPL3.
