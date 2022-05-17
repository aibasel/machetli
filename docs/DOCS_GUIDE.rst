Documentation Guide
===================
This guide is for anyone who wants to contribute to the `documentation of Machetli <https://machetli.readthedocs.io>`_.

The documentation is built with `Sphinx <https://sphinx-doc.org>`_, a popular Python documentation generator. Essentially, we use it to automatically parse docstrings, cross-reference code parts and produce an appealing HTML output for the documentation.

Environment
-----------
As specific package versions are required for the documentation to build correctly, we recommend installing the requirements in the ``docs/requirements.txt`` file via ``pip`` inside a `virtual Python environment <https://docs.python.org/3/tutorial/venv.html>`_. For this, make sure you have the Python venv module installed:

.. code-block:: bash

    sudo apt install python3 python3-venv


Create and activate a Python 3 virtual environment for the Machetli documentation:

.. code-block:: bash

    python3 -m venv .docs-env  # or choose any other name for the environment directory
    source .docs-env/bin/activate

If you haven't already, clone `the Machetli repository <https:/github.com/aibasel/machetli>`_ and check out the documentation branch:

.. code-block:: bash

    git clone https://github.com/aibasel/machetli.git
    # or git clone git@github.com:aibasel/machetli.git (clone with SSH)
    cd machetli
    git checkout documentation

Finally, go into the ``docs/`` directory and install the requirements inside the activated environment:

.. code-block:: bash

    cd docs
    pip install --requirement requirements.txt
    # or simply pip install -r requirements.txt

Now you're ready to work on the documentation!

Documenting
-----------
Machetli is documented using two approaches:

- Documenting **via docstrings** and **auto-generating** API documentation from that.
- **Writing structured pages** with explanations and examples.

In both approaches, the used markup language is `reStructuredText <http://docutils.sourceforge.net/rst.html>`_.

API Documentation
.................
If you simply want to work on the API documentation, go to the function, class or method you want to document and document it via docstrings. There are plenty of examples under the API section of the existing `documentation <https://machetli.readthedocs.io>`_ (click on ``[source]`` to see the docstrings). You can use reStructuredText inside the docstrings to add styling and links to other parts of the documentation or to websites.

After writing the docstrings, you can `auto-generate documentation <https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc>`_ on different levels (module, class, etc.). As an example, here is how this was done for the :mod:`machetli.parser` module:

.. 
  literalinclude:: machetli.parser.rst
    :language: reST
    :caption:

To be displayed in the documentation, the ``machetli.parser.rst`` file displayed above must be included in the ``index.rst`` file:

.. literalinclude:: index.rst
    :language: reST
    :caption:
    :emphasize-lines: 17

Writing Pages
.............
As mentioned before, we can also use reStructuredText to create entire pages that are then built by Sphinx. Here is the markup for the :ref:`section on successor generators <how_does_it_work:Successor Generators>` in the :doc:`how_does_it_work` page:

.. literalinclude:: how_does_it_work.rst
    :language: reST
    :caption:
    :lines: 49-79

Just to highlight a few markup options:

- ``--------------------`` below ``Successor Generators`` describes a header.
- ``:class:`SuccessorGenerator<machetli.planning.generators.SuccessorGenerator>``` creates a reference to the :class:`SuccessorGenerator<machetli.planning.generators.SuccessorGenerator>` class.
- With ``.. code-block::`` you can create highlighted code blocks like in the :ref:`DOCS_GUIDE:Environment` section.
- ``:mod:`machetli.planning.generators``` creates a reference to the :mod:`machetli.planning.generators` module.

Conclusion
----------
Sphinx combined with reStructuredText provides a very powerful toolbox for documenting Machetli. After a small learning curve, you also should be able to work on this project's documentation. A few helpful resources are:

- The existing Machetli documentation `on GitHub <https://github.com/aibasel/machetli/tree/main/docs>`_.
- `Sphinx documentation <https://sphinx-doc.org>`_.
- `reStructuredText documentation <http://docutils.sourceforge.net/rst.html>`_.