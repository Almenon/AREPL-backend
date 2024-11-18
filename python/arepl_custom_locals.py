from copy import deepcopy
from os import path
import arepl_overloads
from arepl_pickler import specialVars

_starting_locals = {}
for var in specialVars:
    _starting_locals[var] = locals()[var]


def get_normal_starting_locals(filePath: str):
    """
    returns the starting locals one would see on a normal run of python (without arepl)
    """
    custom_locals = deepcopy(_starting_locals)
    custom_locals["__name__"] = "__main__"
    custom_locals["__loader__"].name = "__main__"
    del custom_locals["__spec__"]

    custom_locals["__file__"] = filePath
    if filePath:
        custom_locals["__loader__"].path = path.basename(filePath)

    return custom_locals


def inject_overloads(custom_locals):
    custom_locals["help"] = arepl_overloads.help_overload
    custom_locals["input"] = arepl_overloads.input_overload
    custom_locals["howdoi"] = arepl_overloads.howdoi_wrapper
