from sys import version
from sys import builtin_module_names
from sys import modules
import pkg_resources
from stdlib_list import stdlib_list

import types

def getNonUserModules():
    """returns a set of all modules not written by the user (aka all builtin and pip modules)
    
    Returns:
        set -- set of module names
    """

    pipModules = [d.project_name for d in pkg_resources.working_set] # pylint: disable=E1133
    
    specialCases = [
        'pkg_resources', # part of setuptools, but not listed ANYWHERE
        'jsonpickle', # hardcoded as part of AREPL
        'stdlib_list', # hardcoded as part of AREPL
        'arepldump' # AREPL registers it as module but not in pipModules for some reason
    ]

    moreBuiltinModules = stdlib_list(version[:3])
    # moreBuiltinModules contains modules in libs folder, among many others

    evenMoreBuiltinModules = [k for k in modules]
    # how many damn modules are there???

    return set(pipModules + 
            list(builtin_module_names) + 
            moreBuiltinModules +
            evenMoreBuiltinModules +
            specialCases)

def getImportedModules():
    """returns a set of imported modules by looking through globals()
    """
    importedModules = set()

    for _, val in globals().items():
        try:
            # if a user imports a func from a module
            # ex: from json import loads
            # then we have to look at __module__ to see the import
            if val.__module__ != "__main__":
                importedModules.add(val.__module__)
        except AttributeError:
            pass 
        if isinstance(val, types.ModuleType):
            importedModules.add(val.__name__)

    return importedModules