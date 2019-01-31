from copy import deepcopy
from customHandlers import handlers
from importlib import util #https://stackoverflow.com/questions/39660934/error-when-using-importlib-util-to-check-for-library
import json
import jsonpickle
import traceback
from math import isnan
import ast
from time import time
import asyncio
import os
from sys import path, modules, argv
from contextlib import contextmanager
from moduleLogic import getNonUserModules
import inspect


if util.find_spec('howdoi') is not None:
    from howdoi import howdoi

#####################################
"""
This file is the heart of AREPL.
It accepts python code through stdin, runs it, and prints out the local variables.
Along the way I check if I haved saved the locals from a previous run and use those if present
"""
#####################################


class execArgs(object):

    # HALT! do NOT change this without changing corresponding type in the frontend!
    def __init__(self, savedCode, evalCode, filePath='', *args, **kwargs):
        self.savedCode = savedCode
        self.evalCode = evalCode
        self.filePath = filePath


class returnInfo:

    # HALT! do NOT change this without changing corresponding type in the frontend!
    def __init__(self, userError, userVariables, execTime, totalTime, internalError=None, caller='<module>',
                 lineno=-1, done=True, count=-1, *args, **kwargs):
        """
        :param userVariables: JSON string
        :param count: iteration number, used when dumping info at a specific point.
        :type userError: str
        :type userVariables: str
        :type execTime: int
        :type totalTime: int
        :type internalError: str
        :type caller: str
        :type lineno: int
        :type done: bool
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


class customPickler(jsonpickle.pickler.Pickler):
    """
    encodes float values like inf / nan as strings to follow JSON spec while keeping meaning
    Im doing this in custom class because handlers do not fire for floats
    """

    inf = float('inf')
    negativeInf = float('-inf')

    def _get_flattener(self, obj):
        if type(obj) == type(float()):
            if obj == self.inf:
                return lambda obj: 'Infinity'
            if obj == self.negativeInf:
                return lambda obj: '-Infinity'
            if isnan(obj):
                return lambda obj: 'NaN'
        return super(customPickler, self)._get_flattener(obj)


class UserError(Exception):
    """
    user errors should be caught and re-thrown with this
    Be warned that this exception can throw an exception.  Yes, you read that right.  I apolagize in advance.
    :raises: ValueError (varsSoFar gets pickled into JSON, which may result in any number of errors depending on what types are inside)
    """

    def __init__(self, message, varsSoFar={}):
        super().__init__(message)
        self.varsSoFar = pickle_user_vars(varsSoFar)


if util.find_spec('numpy') is not None:
    import jsonpickle.ext.numpy as jsonpickle_numpy
    jsonpickle_numpy.register_handlers()

if util.find_spec('pandas') is not None:
    import jsonpickle.ext.pandas as jsonpickle_pandas
    jsonpickle_pandas.register_handlers()

jsonpickle.pickler.Pickler = customPickler
jsonpickle.set_encoder_options('json', ensure_ascii=False)
jsonpickle.set_encoder_options('json', allow_nan=False) # nan is not deseriazable by javascript
for handler in handlers:
    jsonpickle.handlers.register(handler['type'], handler['handler'])

# copy all special vars (we want execd code to have similar locals as actual code)
# not copying builtins cause exec adds it in
# also when specialVars is deepCopied later on deepcopy cant handle builtins anyways
startingLocals = {}
specialVars = ['__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__']
for var in specialVars:
    startingLocals[var] = locals()[var]

oldSavedLines = []
savedLocals = {}

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
        parser = howdoi.get_parser()
        args = vars(parser.parse_args(strArg.split(' ')))
        returnVal = howdoi.howdoi(args)

    print(returnVal)
    return returnVal # not actually necessary but nice for unit testing


startingLocals['help'] = helpOverload
startingLocals['input'] = inputOverload
startingLocals['howdoi'] = howdoiWrapper


def get_imports(parsedText, text):
    """
    :param parsedText: the result of ast.parse(text)
    :returns: empty string if no imports, otherwise string containing all imports
    """

    child_nodes = [l for l in ast.iter_child_nodes(parsedText)]

    imports = []
    savedCode = text.split('\n')
    for node in child_nodes:
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            importLine = savedCode[node.lineno - 1]
            imports.append(importLine)

    imports = '\n'.join(imports)
    return imports


def exec_saved(savedLines):
    savedLocals = deepcopy(startingLocals)
    try:
        exec(savedLines, savedLocals)
    except Exception:
        errorMsg = traceback.format_exc()
        raise UserError(errorMsg, savedLocals)

    # deepcopy cant handle imported modules, so remove them
    savedLocals = {k:v for k,v in savedLocals.items() if str(type(v)) != "<class 'module'>"}

    return savedLocals


def get_eval_locals(savedLines):
    """
    If savedLines is changed, rexecutes saved lines and returns resulting local variables.
    If savedLines is unchanged, returns the saved locals.
    If savedLines is empty, simply returns the original startingLocals.
    """
    global oldSavedLines
    global savedLocals

    # "saved" code we only ever run once and save locals, vs. codeToExec which we exec as the user types
    # although if saved code has changed we need to re-run it
    if savedLines != oldSavedLines:
        savedLocals = exec_saved(savedLines)
        oldSavedLines = savedLines

    if savedLines != "":
        return deepcopy(savedLocals)
    else:
        return deepcopy(startingLocals)


def pickle_user_vars(userVars):
    # filter out non-user vars, no point in showing them
    userVariables = {k:v for k,v in userVars.items() if str(type(v)) != "<class 'module'>"
                     and str(type(v)) != "<class 'function'>"
                     and k not in specialVars+['__builtins__']}

    # json dumps cant handle any object type, so we need to use jsonpickle
    # still has limitations but can handle much more
    return jsonpickle.encode(userVariables, max_depth=100) # any depth above 245 resuls in error and anything above 100 takes too long to process


def copy_saved_imports_to_exec(codeToExec, savedLines):
    """
    copies imports in savedLines to the top of codeToExec.
    If savedLines is empty this function does nothing.
    :raises: SyntaxError if err in savedLines
    """
    if savedLines.strip() != "":
        try:
            savedCodeAST = ast.parse(savedLines)
        except SyntaxError:
            errorMsg = traceback.format_exc()
            raise UserError(errorMsg)

        imports = get_imports(savedCodeAST, savedLines)
        codeToExec = imports + '\n' + codeToExec

        # to make sure line # in errors is right we need to pad codeToExec with newlines
        numLinesToAdd = len(savedLines.split('\n')) - len(imports.split('\n'))
        for i in range(numLinesToAdd):
            codeToExec = '\n' + codeToExec

    return codeToExec


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
            except os.error:
                pass


def exec_input(codeToExec, savedLines="", filePath=""):
    """
    returns info about the executed code (local vars, errors, and timing)
    :rtype: returnInfo
    """
    global areplInputIterator

    argv[0] = filePath # see https://docs.python.org/3/library/sys.html#sys.argv
    startingLocals['__file__'] = filePath

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
            errorMsg = traceback.format_exc()
            raise UserError(errorMsg, evalLocals)

        finally:
            try:
                # areplDump library keeps state internally
                # because python caches imports the state is kept inbetween runs
                # we do not want that, areplDump should reset each run
                del modules['arepldump']
            except KeyError:
                pass # they have not imported it, whatever

            importedModules = set(modules) - origModules
            userModules = importedModules - nonUserModules

            # user might have changed user module inbetween arepl runs
            # so we clear them to reload import each time
            for userModule in userModules:
                try:
                    del modules[userModule]
                except KeyError:
                    pass # it's not worth failing AREPL over

            # clear mock stdin for next run
            areplInputIterator = None

    userVariables = pickle_user_vars(evalLocals)

    return returnInfo("", userVariables, execTime, None)


def print_output(output):
    """
    turns output into JSON and prints it
    """
    # 6q3co7 signifies to frontend that stdout is not due to a print in user's code
    print('6q3co7' + json.dumps(output, default=lambda x: x.__dict__))


if __name__ == '__main__':

    while True:

        try:
            data = json.loads(input())
            data = execArgs(**data)
        except json.JSONDecodeError as e:
            # probably just due to user passing in stdin to program without input
            # in which case program completes and we get the stdin, which we ignore
            # frontend relies on error message to check for this error so
            # don't change without also changing index.ts!
            print_output(returnInfo("", "{}", None, None, 'json error with stdin: ' + str(e), done=False))
            continue

        start = time()
        myReturnInfo = returnInfo("", "{}", None, None)

        try:
            myReturnInfo = exec_input(data.evalCode, data.savedCode, data.filePath)
        except (KeyboardInterrupt, SystemExit):
            raise
        except UserError as e:
            myReturnInfo.userError = str(e)
            myReturnInfo.userVariables = e.varsSoFar
        except Exception:
            errorMsg = traceback.format_exc()
            myReturnInfo.internalError = "Sorry, AREPL has ran into an error\n\n" + errorMsg

        myReturnInfo.totalPyTime = time() - start

        print_output(myReturnInfo)
