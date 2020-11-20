from sys import modules

# MUST be done first thing to avoid other modules getting into cache
modules_to_keep = set([module_name for module_name in modules])
# below line needed so test_jsonpickle_err_doesnt_break_arepl test passes
# we want to keep arepl imports in the cache
modules_to_keep.update(
    (
        "arepl_overloads",
        "arepl_pickler",
        "arepl_saved",
        "arepl_settings",
        "arepl_user_error",
        "arepl_result_stream",
        "arepl_jsonpickle",
        "arepl_jsonpickle.util",
        "arepl_jsonpickle.handlers",
        "arepl_jsonpickle.version",
        "arepl_jsonpickle.pickler",
        "arepl_jsonpickle.backend",
        "arepl_jsonpickle.tags",
        "arepl_jsonpickle.compat",
        "arepl_jsonpickle.unpickler",
        "arepl_jsonpickle.ext",
        "arepl_jsonpickle.ext.pandas",
        "arepl_jsonpickle.ext.numpy",
        "typing",  # for some reason i can't clear this or jsonpickle breaks
    )
)
# when arepl is ran via unit test/debugging some extra libraries might be in modules_to_keep
# in normal run it is not in there so we remove it
modules_to_keep.difference_update(
    {
        "arepl_dump",
        "decimal",
        "asyncio.constants",
        "asyncio.format_helpers",
        "asyncio.base_futures",
        "asyncio.log",
        "asyncio.coroutines",
        "asyncio.exceptions",
        "asyncio.base_tasks",
        "_asyncio",
        "asyncio.events",
        "asyncio.futures",
        "asyncio.protocols",
        "asyncio.transports",
        "asyncio.sslproto",
        "asyncio.locks",
        "asyncio.tasks",
        "asyncio.staggered",
        "asyncio.trsock",
        "asyncio.base_events",
        "asyncio.runners",
        "asyncio.queues",
        "asyncio.streams",
        "asyncio.subprocess",
        "asyncio.base_subprocess",
        "asyncio.proactor_events",
        "asyncio.selector_events",
        "asyncio.windows_utils",
        "asyncio.windows_events",
        "asyncio",
    }
)

import asyncio

try:
    # import fails in python 3.6
    import contextvars
except ImportError:
    pass
from copy import deepcopy
from importlib import (
    util,
    reload,
)  # https://stackoverflow.com/questions/39660934/error-when-using-importlib-util-to-check-for-library
import json
import traceback
from time import time
import asyncio
from io import TextIOWrapper
import os
import sys
from sys import path, argv, exc_info
from typing import Any, Dict, FrozenSet, Set
from contextlib import contextmanager

# do NOT use from arepl_overloads import arepl_input_iterator
# it will recreate arepl_input_iterator and we need the original
import arepl_overloads
from arepl_pickler import specialVars, pickle_user_vars, pickle_user_error
import arepl_saved as saved
from arepl_settings import get_settings, update_settings
from arepl_user_error import UserError
import arepl_result_stream

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


class ExecArgs(object):

    # HALT! do NOT change this without changing corresponding type in the frontend! <----
    # Also note that this uses camelCase because that is standard in JS frontend
    def __init__(self, evalCode: str, savedCode="", filePath="", usePreviousVariables=False, *args, **kwargs):
        self.savedCode = savedCode
        self.evalCode = evalCode
        self.filePath = filePath
        self.usePreviousVariables = usePreviousVariables
        # HALT! do NOT change this without changing corresponding type in the frontend! <----


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


saved.starting_locals["help"] = arepl_overloads.help_overload
saved.starting_locals["input"] = arepl_overloads.input_overload
saved.starting_locals["howdoi"] = arepl_overloads.howdoi_wrapper

eval_locals = deepcopy(saved.starting_locals)

noGlobalVarsMsg = {"zz status": "AREPL is configured to not show global vars"}

try:
    run_context = contextvars.Context()
except NameError:
    run_context = None


def exec_input(exec_args: ExecArgs):
    """
    returns info about the executed code (local vars, errors, and timing)
    :rtype: returnInfo
    """
    global eval_locals
    global run_context

    argv[0] = exec_args.filePath
    # see https://docs.python.org/3/library/sys.html#sys.argv
    saved.starting_locals["__file__"] = exec_args.filePath
    if exec_args.filePath:
        saved.starting_locals["__loader__"].path = os.path.basename(exec_args.filePath)

    if not exec_args.usePreviousVariables:
        eval_locals = saved.get_eval_locals(exec_args.savedCode)

    # re-import imports. (pickling imports from saved code was unfortunately not possible)
    exec_args.evalCode = saved.copy_saved_imports_to_exec(exec_args.evalCode, exec_args.savedCode)

    # clear new modules from last run each run has same fresh start
    current_module_names = set([module_name for module_name in modules])
    new_modules = current_module_names - modules_to_keep
    for module_name in new_modules:
        del modules[module_name]

    # not sure why i need to do this when module was deleted
    # but if I don't next run will say event loop closed
    asyncio.set_event_loop(asyncio.new_event_loop())

    with script_path(os.path.dirname(exec_args.filePath)):
        if not exec_args.usePreviousVariables and run_context is not None:
            run_context = contextvars.Context()
        try:
            start = time()
            if run_context is not None:
                run_context.run(exec, exec_args.evalCode, eval_locals)
            else:
                # python 3.6 fallback
                exec(exec_args.evalCode, eval_locals)
            execTime = time() - start
        except BaseException:
            execTime = time() - start
            _, exc_obj, exc_tb = exc_info()
            if not get_settings().show_global_vars:
                raise UserError(exc_obj, exc_tb, noGlobalVarsMsg, execTime)
            else:
                raise UserError(exc_obj, exc_tb, eval_locals, execTime)

        finally:

            if sys.stdout.flush and callable(sys.stdout.flush):
                # a normal program will flush at the end of the run
                # arepl never stops so we have to do it manually
                sys.stdout.flush()

            saved.arepl_store = eval_locals.get("arepl_store")

            # clear mock stdin for next run
            arepl_overloads.arepl_input_iterator = None

    if get_settings().show_global_vars:
        userVariables = pickle_user_vars(
            eval_locals, get_settings().default_filter_vars, get_settings().default_filter_types,
        )
    else:
        userVariables = pickle_user_vars(
            noGlobalVarsMsg, get_settings().default_filter_vars, get_settings().default_filter_types,
        )

    return ReturnInfo("", userVariables, execTime, None)


def print_output(output: object):
    """
    turns output into JSON and sends it to result stream
    """
    # We use result stream because user might use stdout and we don't want to conflict
    print(
        json.dumps(output, default=lambda x: x.__dict__), file=arepl_result_stream.get_result_stream(), flush=True,
    )


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
        return_info.internalError = "Sorry, AREPL has ran into an error\n\n" + traceback.format_exc()

    return_info.totalPyTime = time() - start

    print_output(return_info)
    return return_info


if __name__ == "__main__":
    encoding = None
    # arepl should treat stdout as tty device
    # windows uses utf8 as encoding for tty device
    # so we need to manually specify it in that case
    # https://docs.python.org/3/library/sys.html#sys.stdout
    if sys.platform == "win32":
        encoding = "utf8"
    # arepl is ran via node so python thinks stdout is not a tty device and uses full buffering
    # We want users to see output in real time so we change to line buffering
    # todo: once python3.7 is supported use .reconfigure() instead
    sys.stdout = TextIOWrapper(open(sys.stdout.fileno(), "wb"), line_buffering=True, encoding=encoding)
    # Arepl node code will spawn process with a extra pipe for results
    # This is to avoid results conflicting with user writes to stdout
    arepl_result_stream.open_result_stream()
    while True:
        main(input())
