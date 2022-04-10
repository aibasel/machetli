from setuptools import setup, find_packages

setup(
    name="machetli",
    description="Locate bugs in your program",
    author="Lucas Galery Käser",
    author_email="lucas.galerykaeser@gmail.com",
    url="https://github.com/aibasel/machetli",
    license="GPL3+",
    packages=find_packages(),
    python_requires=">=3.7",
    include_package_data=True,
    package_data={
        "machetli": ["grid/slurm-array-job.template"],
    },
)
