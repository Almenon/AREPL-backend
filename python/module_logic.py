from sys import version
from sys import builtin_module_names
from sys import modules
from pkgutil import iter_modules
from stdlib_list import stdlib_list


def getNonUserModules():
    """returns a set of all modules not written by the user (aka all builtin and pip modules)
    
    Returns:
        set -- set of module names
    """
    # p[1] is name
    pipModules = [p[1] for p in iter_modules()] # pylint: disable=E1133

    specialCases = [
        'jsonpickle', # hardcoded as part of AREPL
        'stdlib_list', # hardcoded as part of AREPL
        'python_evaluator', # hardcoded as part of AREPL
    ]

    moreBuiltinModules = stdlib_list(version[:3], fallback=True)
    # moreBuiltinModules contains modules in libs folder, among many others

    evenMoreBuiltinModules = [k for k in modules]
    # how many damn modules are there???

    return set(
        pipModules
        + list(builtin_module_names)
        + moreBuiltinModules
        + evenMoreBuiltinModules
        + specialCases
    )
