# Publishing a new version:
#
# 1. Update the version tag in this file.
# 2. Remove the `dist/` and the `machetli.egg-info` directories
# 3. Run the following steps (needs `pip install build twine`):
#
#     $ python3 -m build
#     $ python3 -m twine upload dist/*
#
# 4. Enter the API token

from pathlib import Path

from setuptools import setup, find_packages

long_description = Path("README.rst").read_text(encoding="utf-8")

setup(
    name="machetli",
    version="0.10",
    description="Locate bugs in your program",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Lucas Galery Käser",
    author_email="lucas.galerykaeser@gmail.com",
    url="https://github.com/aibasel/machetli",
    license="GPL3+",
    project_urls={
        "Documentation": "https://machetli.readthedocs.io/",
    },
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering",
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires = ["questionary >= 2.1.0", "CT3 >= 3.4"],
    include_package_data=True,
    package_data={
        "machetli": [
            "templates/slurm-array-job.template",
            "templates/interview/evaluator.py.tmpl",
            "templates/interview/run.py.tmpl",
        ],
    },
    entry_points={
        "console_scripts": [
            "machetli = machetli.interview:main",
        ],
    },
)
