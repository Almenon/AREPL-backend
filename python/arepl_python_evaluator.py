from copy import deepcopy
from importlib import (
    util,
)  # https://stackoverflow.com/questions/39660934/error-when-using-importlib-util-to-check-for-library
import json
import traceback
from time import time
import asyncio
from io import TextIOWrapper
import os
import sys
from sys import path, modules, argv, version_info, exc_info
from typing import Any, Dict, FrozenSet, Set
from contextlib import contextmanager
from arepl_module_logic import get_non_user_modules

# do NOT use from arepl_overloads import arepl_input_iterator
# it will recreate arepl_input_iterator and we need the original
import arepl_overloads
from arepl_pickler import specialVars, pickle_user_vars, pickle_user_error
import arepl_saved as saved
from arepl_settings import get_settings, update_settings
from arepl_user_error import UserError

if util.find_spec("howdoi") is not None:
    from howdoi import howdoi  # pylint: disable=import-error

#####################################
"""
This file is the heart of AREPL.
It accepts python code through stdin, runs it, and prints out the local variables.
Along the way I check if I haved saved the locals from a previous run and use those if present
"""
#####################################


class ReturnInfo:

    # HALT! do NOT change this without changing corresponding type in the frontend!
    # Also note that this uses camelCase because that is standard in JS frontend
    def __init__(
        self,
        userError: str,
        userVariables: dict,
        execTime: float,
        totalPyTime: float,
        internalError: str = None,
        caller="<module>",
        lineno=-1,
        done=True,
        count=-1,
        *args,
        **kwargs
    ):
        """
        :param userVariables: JSON string
        :param count: iteration number, used when dumping info at a specific point.
        """
        self.userError = userError
        self.userVariables = userVariables
        self.execTime = execTime
        self.totalPyTime = totalPyTime
        self.internalError = internalError
        self.caller = caller
        self.lineno = lineno
        self.done = done
        self.count = count


if version_info[0] < 3 or (version_info[0] == 3 and version_info[1] < 5):
    # need at least 3.5 for typing
    exMsg = "Must be using python 3.5 or later. You are using " + str(version_info)
    print(ReturnInfo("", "{}", None, None, exMsg))
    raise Exception(exMsg)


class ExecArgs(object):

    # HALT! do NOT change this without changing corresponding type in the frontend! <----
    # Also note that this uses camelCase because that is standard in JS frontend
    def __init__(
        self,
        evalCode: str,
        savedCode="",
        filePath="",
        usePreviousVariables=False,
        *args,
        **kwargs
    ):
        self.savedCode = savedCode
        self.evalCode = evalCode
        self.filePath = filePath
        self.usePreviousVariables = usePreviousVariables
        # HALT! do NOT change this without changing corresponding type in the frontend! <----


nonUserModules = get_non_user_modules()
origModules = frozenset(modules)

saved.starting_locals["help"] = arepl_overloads.help_overload
saved.starting_locals["input"] = arepl_overloads.input_overload
saved.starting_locals["howdoi"] = arepl_overloads.howdoi_wrapper

eval_locals = deepcopy(saved.starting_locals)


@contextmanager
def script_path(script_dir: str):
    """
        Context manager for adding a dir to the sys path
        and restoring it afterwards. This trick allows
        relative imports to work on the target script.
        if script_dir is empty function will do nothing
        Slightly modified from wolf's script_path (see https://github.com/Duroktar/Wolf)
        Exception-safe (os.error will not be raised)
    """
    if script_dir is None or script_dir == "":
        yield
    else:
        arepl_dir = path[0]
        path[0] = script_dir
        path.append(arepl_dir)
        try:
            original_cwd = os.getcwd()
            os.chdir(script_dir)
        except os.error:
            # no idea why this would happen but a user got this error once
            # this func is not critical to arepl so we dont want error to bubble up
            pass

        try:
            yield
        finally:
            if path[-1] == arepl_dir:
                path.pop()
            path[0] = arepl_dir
            try:
                os.chdir(original_cwd)
            except os.error:
                pass


noGlobalVarsMsg = {"zz status": "AREPL is configured to not show global vars"}


def exec_input(exec_args: ExecArgs):
    """
    returns info about the executed code (local vars, errors, and timing)
    :rtype: returnInfo
    """
    global eval_locals

    argv[0] = exec_args.filePath
    # see https://docs.python.org/3/library/sys.html#sys.argv
    saved.starting_locals["__file__"] = exec_args.filePath
    if exec_args.filePath:
        saved.starting_locals["__loader__"].path = os.path.basename(exec_args.filePath)

    if not exec_args.usePreviousVariables:
        eval_locals = saved.get_eval_locals(exec_args.savedCode)

    # re-import imports. (pickling imports from saved code was unfortunately not possible)
    exec_args.evalCode = saved.copy_saved_imports_to_exec(
        exec_args.evalCode, exec_args.savedCode
    )

    # repoen revent loop in case user closed it in last run
    asyncio.set_event_loop(asyncio.new_event_loop())

    with script_path(os.path.dirname(exec_args.filePath)):
        try:
            start = time()
            exec(exec_args.evalCode, eval_locals)
            execTime = time() - start
        except BaseException:
            execTime = time() - start
            _, exc_obj, exc_tb = exc_info()
            if not get_settings().showGlobalVars:
                raise UserError(exc_obj, exc_tb, noGlobalVarsMsg, execTime)
            else:
                raise UserError(exc_obj, exc_tb, eval_locals, execTime)

        finally:

            saved.arepl_store = eval_locals.get("arepl_store")

            try:
                # arepl_dump library keeps state internally
                # because python caches imports the state is kept inbetween runs
                # we do not want that, arepl_dump should reset each run
                del modules["arepl_dump"]
            except KeyError:
                pass  # they have not imported it, whatever

            importedModules = set(modules) - origModules
            userModules = importedModules - nonUserModules

            # user might have changed user module inbetween arepl runs
            # so we clear them to reload import each time
            for userModule in userModules:
                try:
                    # #70: nonUserModules does not list submodules
                    # so we have to extract base module and use that
                    # to skip any nonUserModules
                    baseModule = userModule.split(".")[0]
                    if len(baseModule) > 1:
                        if baseModule in nonUserModules:
                            continue
                    del modules[userModule]
                except KeyError:
                    pass  # it's not worth failing AREPL over

            # clear mock stdin for next run
            arepl_overloads.arepl_input_iterator = None

    if get_settings().showGlobalVars:
        userVariables = pickle_user_vars(
            eval_locals,
            get_settings().default_filter_vars,
            get_settings().default_filter_types,
        )
    else:
        userVariables = pickle_user_vars(
            noGlobalVarsMsg,
            get_settings().default_filter_vars,
            get_settings().default_filter_types,
        )

    return ReturnInfo("", userVariables, execTime, None)


def print_output(output: object):
    """
    turns output into JSON and prints it
    """
    # 6q3co7 signifies to frontend that stdout is not due to a print in user's code
    print("6q3co7" + json.dumps(output, default=lambda x: x.__dict__))


def main(json_input: str):
    data = json.loads(json_input)
    execArgs = ExecArgs(**data)
    update_settings(data)

    start = time()
    return_info = ReturnInfo("", "{}", None, None)

    try:
        return_info = exec_input(execArgs)
    except (KeyboardInterrupt, SystemExit):
        raise
    except UserError as e:
        return_info.userError = pickle_user_error(e.traceback_exception)
        return_info.userErrorMsg = e.friendly_message
        return_info.userVariables = e.varsSoFar
        return_info.execTime = e.execTime
    except Exception as e:
        return_info.internalError = (
            "Sorry, AREPL has ran into an error\n\n" + traceback.format_exc()
        )

    return_info.totalPyTime = time() - start

    print_output(return_info)
    return return_info


if __name__ == "__main__":
    # arepl is ran via node so python thinks stdout is not a tty device and uses full buffering
    # We want users to see output in real time so we change to line buffering
    # todo: once python3.7 is supported use .reconfigure() instead
    sys.stdout = TextIOWrapper(open(sys.stdout.fileno(), "wb"), line_buffering=True)
    while True:
        main(input())
