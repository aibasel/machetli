# Re-building the gif files

* Install VHS: https://github.com/charmbracelet/vhs
* Change directory to the `_vhs` directory
* Make sure the directory is clean (running the scripts creates a directory .venv and a directory machetli_scripts)
* Run `vhs install.tape` then `vhs interview.tape`


# Automating the process
So far, we manually copied the files into the doc directory. We could probably
automate the process (there is a VHS docker image) as part of the build
Makefile but it may not be worth the effort.
