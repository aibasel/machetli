Documentation Guide
===================
This guide is for anyone who wants to contribute to the `documentation of
Machetli <https://machetli.readthedocs.io>`_.

The documentation is built with `Sphinx <https://sphinx-doc.org>`_, a popular
Python documentation generator. Essentially, we use it to automatically parse
docstrings, cross-reference code parts and produce an appealing HTML output for
the documentation.

One-time Setup
--------------
To generate the documentation locally, you need to install sphinx. We recommend
to do so in a virtual environment. Setting this up is only required once.

.. code-block:: bash

    # Install the venv module for Python 3.
    sudo apt install python3 python3-venv
    # Create a virtual environment in docs/.docs-env
    # Please use this location, so generated files are correctly ignored by git.
    cd docs
    python3 -m venv .docs-env
    source .docs-env/bin/activate
    # Install Sphinx. The latest release should work fine but in case there are
    # issues, you can install the versions specified in requirements.txt like
    # this (didn't work on Ubuntu 22.04):
    #   pip install --requirement requirements.txt
    pip install Sphinx sphinx_rtd_theme

Now you're ready to work on the documentation!

Building
--------
To update the online documentation, just commit and push to the repository,
readthedocs.org will detect the change and rebuild the documentation
automatically.

To build the documentation locally, activate the virtual environment and use the
Makefile in `docs/`. You can then find the created files in `_build/html`.

.. code-block:: bash

    cd docs
    source .docs-env/bin/activate
    make html
    firefox _build/html/index.html


Documenting
-----------
Machetli is documented using two approaches:

- API documentation is **auto-generated** from **docstrings** in the code.
- User documentation is written as explicit rst documents in the directory *docs*.

In both approaches, the used markup language is `reStructuredText <http://docutils.sourceforge.net/rst.html>`_.

API Documentation
^^^^^^^^^^^^^^^^^
If you simply want to work on the API documentation, go to the function, class
or method you want to document and document it via docstrings. There are plenty
of examples under the API section of the existing `documentation
<https://machetli.readthedocs.io>`_ (click on ``[source]`` to see the
docstrings). You can use reStructuredText inside the docstrings to add styling
and links to other parts of the documentation or to websites.


Writing Pages
^^^^^^^^^^^^^
As mentioned before, we can also use reStructuredText to create entire pages
that are then built by Sphinx. Follow the example of other rst files in *docs*.


Just to highlight a few markup options:

- Lines of ``====``, ``----``,  or ``^^^^`` below a line turn that line into a
  (sub)section header.
- With ``.. code-block::`` you can create highlighted code blocks.
- ``.. _usage-evaluator:`` creates an internal label and ``:ref:`how to write an evaluator <usage-evaluator>``` creates a link to that label.
- ```documentation <https://machetli.readthedocs.io>`_`` creates a link to the 
  `documentation <https://machetli.readthedocs.io>`_
- ``:mod:`machetli.successors``` creates a reference to the
  :mod:`machetli.successors` module.
- ``:class:`SuccessorGenerator<machetli.successors.SuccessorGenerator>```
  creates a reference to the
  :class:`SuccessorGenerator<machetli.successors.SuccessorGenerator>` class.

Conclusion
----------
- `Sphinx documentation <https://sphinx-doc.org>`_.
- `reStructuredText documentation <http://docutils.sourceforge.net/rst.html>`_.