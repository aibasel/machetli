from collections.abc import Sequence


def make_iterable(arg):
    return tuple(arg) if isinstance(arg, Sequence) and not isinstance(arg, str) else (arg,)
