from setuptools import setup

setup(
    name="minimizer",
    description="Locate bugs in your program",
    author="Lucas Galery Käser",
    author_email="lucas.galerykaeser@gmail.com",
    url="https://github.com/aibasel/minimizer",
    license="GPL3+",
    packages=["minimizer", "minimizer.grid", "minimizer.planning"],
    install_requires=["lab"],
    python_requires=">=3.7"
)
