from collections.abc import Iterable


def make_iterable(arg):
    return tuple(arg) if isinstance(arg, Iterable) else (arg,)
