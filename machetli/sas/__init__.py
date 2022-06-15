from machetli.sas.files import generate_initial_state, temporary_file, \
    write_file

# We specify the imported functions and classes in __all__ so they will be
# documented when the documentation of this package is generated.
__all__ = ["generate_initial_state", "temporary_file", "write_file"]

def _import_successor_generators():
    # Import all successor generators and put them in the package namespace
    # so users can access them without knowing about the subpackage generators.
    import machetli.sas.generators as generators

    for key, value in generators.__dict__.items():
        if (isinstance(value, type)
            and issubclass(value, generators.SuccessorGenerator)
            and value != generators.SuccessorGenerator):
            __all__.append(key)
            globals()[key] = value

_import_successor_generators()
del _import_successor_generators