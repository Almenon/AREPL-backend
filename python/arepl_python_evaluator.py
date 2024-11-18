from copy import deepcopy
from importlib import (
    util,
)  # https://stackoverflow.com/questions/39660934/error-when-using-importlib-util-to-check-for-library
import json
import traceback
from time import time
from io import TextIOWrapper
import os
import sys
from sys import path, argv, exc_info
from contextlib import contextmanager

# do NOT use from arepl_overloads import arepl_input_iterator
# it will recreate arepl_input_iterator and we need the original
import arepl_overloads
from arepl_pickler import pickle_user_vars, pickle_user_error
from arepl_custom_locals import get_normal_starting_locals, inject_overloads
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
        startResult=False,
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
        self.startResult = startResult


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


noGlobalVarsMsg = {"zz status": "AREPL is configured to not show global vars"}

exec_locals = None

def exec_input(exec_args: ExecArgs):
    """
    returns info about the executed code (local vars, errors, and timing)
    :rtype: returnInfo
    """
    global exec_locals

    # see https://docs.python.org/3/library/sys.html#sys.argv
    argv[0] = exec_args.filePath

    first_run = exec_locals == None
    if first_run or not exec_args.usePreviousVariables:
        # We have to set this on first run.
        # Also if we are not reusing previous variables, we reset this for unit tests
        exec_locals = get_normal_starting_locals(exec_args.filePath)
        inject_overloads(exec_locals)

    with script_path(os.path.dirname(exec_args.filePath)):
        try:
            start = time()
            exec(exec_args.evalCode, exec_locals)
            execTime = time() - start
        except BaseException:
            execTime = time() - start
            _, exc_obj, exc_tb = exc_info()
            if not get_settings().show_global_vars:
                raise UserError(exc_obj, exc_tb, noGlobalVarsMsg, execTime)
            else:
                raise UserError(exc_obj, exc_tb, exec_locals, execTime)
        finally:
            if sys.stdout.flush and callable(sys.stdout.flush):
                # a normal program will flush at the end of the run
                sys.stdout.flush()

            # clear mock stdin for next run
            arepl_overloads.arepl_input_iterator = None

    if get_settings().show_global_vars:
        userVariables = pickle_user_vars(
            exec_locals,
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


def print_output(output: ReturnInfo):
    """
    turns output into JSON and sends it to result stream
    """
    # We use result stream because user might use stdout and we don't want to conflict
    print(
        json.dumps(output, default=lambda x: x.__dict__),
        file=arepl_result_stream.get_result_stream(),
        flush=True,
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

    finished_starting = ReturnInfo("", {}, 0, 0, startResult=True)
    print_output(finished_starting)

    while True:
        main(input())
