============
Installation
============

Machetli requires Python 3.7+ and can be installed with ``pip``.

.. code-block:: bash

    pip install machetli

If you want to avoid changes to your system-wide Python installation you can
install Machetli in a virtual Python environment.

.. code-block:: bash

    # Install Python 3 and virtualenv.
    sudo apt install python3 python3-venv

    # If PYTHONPATH is set, unset it to obtain a clean environment.
    unset PYTHONPATH

    # Create and activate a Python 3 virtual environment for Machetli.
    python3 -m venv --prompt machetli .venv
    source .venv/bin/activate

    # Install Machetli in the virtual environment.
    pip install machetli
