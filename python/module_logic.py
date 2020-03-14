from sys import version
from sys import builtin_module_names
from sys import modules
from pkgutil import iter_modules
from stdlib_list import stdlib_list
from typing import List,Set

def get_non_user_modules() -> Set[str]:
    """returns a set of all modules not written by the user (aka all builtin and pip modules)
    
    Returns:
        set -- set of module names
    """
    # p[1] is name
    pip_modules: List[str] = [p[1] for p in iter_modules()]  # pylint: disable=E1133

    special_cases: List[str] = [
        "jsonpickle",  # hardcoded as part of AREPL
        "stdlib_list",  # hardcoded as part of AREPL
        "python_evaluator",  # hardcoded as part of AREPL
    ]

    more_builtin_modules = stdlib_list(version[:3], fallback=True)
    # more_builtin_modules contains modules in libs folder, among many others

    even_more_builtin_modules: List[str] = [k for k in modules]
    # how many damn modules are there???

    return set(
        pip_modules + list(builtin_module_names) + more_builtin_modules + even_more_builtin_modules + special_cases
    )
