from copy import deepcopy
from importlib import util #https://stackoverflow.com/questions/39660934/error-when-using-importlib-util-to-check-for-library
import json
import traceback
from time import time
import asyncio
import os
from sys import path, modules, argv, version_info, exc_info
from contextlib import contextmanager
from module_logic import getNonUserModules
import inspect

from saved import get_starting_locals
from saved import get_eval_locals
from saved import copy_saved_imports_to_exec
from saved import startingLocals
from saved import areplStore
from pickler import specialVars, pickle_user_vars, pickle_user_error
from user_error import UserError

if util.find_spec('howdoi') is not None:
    from howdoi import howdoi # pylint: disable=import-error

#####################################
"""
This file is the heart of AREPL.
It accepts python code through stdin, runs it, and prints out the local variables.
Along the way I check if I haved saved the locals from a previous run and use those if present
"""
#####################################


class returnInfo:

    # HALT! do NOT change this without changing corresponding type in the frontend!
    def __init__(self, userError, userVariables, execTime, totalTime, internalError=None, caller='<module>',
                 lineno=-1, done=True, count=-1, *args, **kwargs):
        """
        :param userVariables: JSON string
        :param count: iteration number, used when dumping info at a specific point.
        """
        self.userError = userError
        self.userVariables = userVariables
        self.execTime = execTime
        self.totalTime = totalTime
        self.internalError = internalError
        self.caller = caller
        self.lineno = lineno
        self.done = done
        self.count = count

if version_info[0] < 3 or (version_info[0] == 3 and version_info[1] < 4):
    # need at least 3.5 for typing
    exMsg = "Must be using python 3.4 or later. You are using " + str(version_info)
    print(returnInfo("", "{}", None, None, exMsg))
    raise Exception(exMsg)


class ExecArgs(object):

    # HALT! do NOT change this without changing corresponding type in the frontend! <----
    def __init__(self, savedCode, evalCode, filePath='', usePreviousVariables=False, showGlobalVars=True, *args, **kwargs):
        self.savedCode = savedCode
        self.evalCode = evalCode
        self.filePath = filePath
        self.usePreviousVariables = usePreviousVariables
        self.showGlobalVars = showGlobalVars
        # HALT! do NOT change this without changing corresponding type in the frontend! <----

nonUserModules = getNonUserModules()
origModules = frozenset(modules)

# AREPL-vscode does not support stdin yet so help breaks it
# by overridding help with a non-stdin version we can prevent AREPL-vscode from freezing up
# just a temp fix untill AREPL-vscode supports stdin


def helpOverload(arg=None):
    if arg is None: print("""Welcome to python! :)
If this is your first time using Python, you should definitely check out
the tutorial on the Internet at https://docs.python.org/3.7/tutorial/.

AREPL uses a custom implementation of help which does not have all the features of the interpreter help. 
But AREPL's help can still give you information on functions / modules / objects you pass into it.""")
    else: print(arg.__doc__)


areplInputIterator = None
def inputOverload(prompt=None):
    """AREPL requires standard_input to be hardcoded, like so: standard_input = 'hello world'; print(input()). You can also hardcode standard_input as a generator or list.
    
    Keyword Arguments:
        prompt {str} --  (default: {None})
    
    Raises:
        StopIteration -- if there is no more input
    
    Returns:
        str
    """
    global areplInputIterator

    if prompt is not None: print(prompt)
    try:
        if areplInputIterator is not None:
            try:
                return next(areplInputIterator)
            except StopIteration:
                # give simple user-friendly error, we dont want users worry about error in arepl source code
                raise StopIteration("There is no more input") from None
        else:

            callingFrame = inspect.currentframe().f_back
            standard_input = callingFrame.f_globals['standard_input']

            if type(standard_input) is str:
                areplInputIterator = iter([line for line in standard_input.split('\n')])
            elif callable(standard_input):
                areplInputIterator = standard_input()
            else:
                areplInputIterator = iter([line for line in standard_input])

            return next(areplInputIterator)
    except KeyError:
        print("AREPL requires standard_input to be hardcoded, like so: standard_input = 'hello world'; print(input())")


def howdoiWrapper(strArg):
    """howdoi is meant to be called from the command line - this wrapper lets it be called programatically
    
    Arguments:
        strArg {str} -- search term
    """

    if strArg.lower() == 'use arepl' or strArg.lower() == 'arepl':
        returnVal = 'using AREPL is simple - just start coding and arepl will show you the final state of your variables. For more help see https://github.com/Almenon/AREPL-vscode/wiki'
    else:
        try:
            parser = howdoi.get_parser()
        except NameError as e:
            # alter error to be more readable by user
            e.args = (['howdoi is not installed'])
            raise
            
        args = vars(parser.parse_args(strArg.split(' ')))
        returnVal = howdoi.howdoi(args)

    print(returnVal)
    return returnVal # not actually necessary but nice for unit testing


startingLocals['help'] = helpOverload
startingLocals['input'] = inputOverload
startingLocals['howdoi'] = howdoiWrapper

evalLocals = deepcopy(startingLocals)




@contextmanager
def script_path(script_dir):
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
        try:
            original_cwd = os.getcwd()
            os.chdir(script_dir)
            path.insert(1, script_dir)
        except os.error:
            # no idea why this would happen but a user got this error once
            # this func is not critical to arepl so we dont want error to bubble up
            pass

        try:
            yield
        finally:
            try:
                os.chdir(original_cwd)
                path.remove(script_dir)
            except (os.error, ValueError):
                pass

noGlobalVarsMsg = {'zz status': 'AREPL is configured to not show global vars'}

def exec_input(codeToExec, savedLines="", filePath="", usePreviousVariables=False, showGlobalVars=True):
    """
    returns info about the executed code (local vars, errors, and timing)
    :rtype: returnInfo
    """
    global areplInputIterator
    global areplStore
    global evalLocals

    argv[0] = filePath # see https://docs.python.org/3/library/sys.html#sys.argv
    startingLocals['__file__'] = filePath

    if not usePreviousVariables:
        evalLocals = get_eval_locals(savedLines)

    # re-import imports. (pickling imports from saved code was unfortunately not possible)
    codeToExec = copy_saved_imports_to_exec(codeToExec, savedLines)

    # repoen revent loop in case user closed it in last run
    asyncio.set_event_loop(asyncio.new_event_loop())

    with script_path(os.path.dirname(filePath)):
        try:
            start = time()
            exec(codeToExec, evalLocals)
            execTime = time() - start
        except BaseException:
            execTime = time() - start
            _, exc_obj, exc_tb = exc_info()
            if not showGlobalVars:
                raise UserError(exc_obj, exc_tb, noGlobalVarsMsg, execTime)
            else:
                raise UserError(exc_obj, exc_tb, evalLocals, execTime)

        finally:

            areplStore = evalLocals.get('areplStore', None)

            try:
                # arepl_dump library keeps state internally
                # because python caches imports the state is kept inbetween runs
                # we do not want that, arepl_dump should reset each run
                del modules['arepl_dump']
            except KeyError:
                pass # they have not imported it, whatever

            importedModules = set(modules) - origModules
            userModules = importedModules - nonUserModules

            # user might have changed user module inbetween arepl runs
            # so we clear them to reload import each time
            for userModule in userModules:
                try:
                    # #70: nonUserModules does not list submodules
                    # so we have to extract base module and use that
                    # to skip any nonUserModules
                    baseModule = userModule.split('.')[0]
                    if len(baseModule) > 1:
                        if baseModule in nonUserModules: continue
                    del modules[userModule]
                except KeyError:
                    pass # it's not worth failing AREPL over

            # clear mock stdin for next run
            areplInputIterator = None

    if showGlobalVars:
        userVariables = pickle_user_vars(evalLocals)
    else:
        userVariables = pickle_user_vars(noGlobalVarsMsg)

    return returnInfo("", userVariables, execTime, None)


def print_output(output):
    """
    turns output into JSON and prints it
    """
    # 6q3co7 signifies to frontend that stdout is not due to a print in user's code
    print('6q3co7' + json.dumps(output, default=lambda x: x.__dict__))


if __name__ == '__main__':

    while True:

        data = json.loads(input())
        data = ExecArgs(**data)

        start = time()
        myReturnInfo = returnInfo("", "{}", None, None)

        try:
            myReturnInfo = exec_input(data.evalCode, data.savedCode, data.filePath, data.usePreviousVariables, data.showGlobalVars)
        except (KeyboardInterrupt, SystemExit):
            raise
        except UserError as e:
            myReturnInfo.userError = pickle_user_error(e.traceback_exception)
            myReturnInfo.userErrorMsg = e.friendly_message
            myReturnInfo.userVariables = e.varsSoFar
            myReturnInfo.execTime = e.execTime
        except Exception as e:
            myReturnInfo.internalError = "Sorry, AREPL has ran into an error\n\n" + str(e)

        myReturnInfo.totalPyTime = time() - start

        print_output(myReturnInfo)
