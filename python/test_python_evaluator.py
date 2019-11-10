from os import getcwd, chdir, path, pardir
from sys import version_info, modules
from shutil import rmtree

import pytest
import jsonpickle

import python_evaluator

python_ignore_path = path.join(path.dirname(path.abspath(__file__)), "testDataFiles")

# These tests can be run with pytest


def test_simple_code():
    returnInfo = python_evaluator.exec_input("x = 1")
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == 1


def test_has_error():
    with pytest.raises(python_evaluator.UserError):
        python_evaluator.exec_input("x")


def test_error_has_traceback():
    try:
        python_evaluator.exec_input(
            """
def foo():
    x
foo()
        """
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except python_evaluator.UserError as e:
        assert e.traceback_exception.exc_type == NameError
        assert len(e.traceback_exception.stack) == 2
        assert e.traceback_exception.stack[0].lineno == 4
        assert e.traceback_exception.stack[1].lineno == 3
        assert "name 'x' is not defined" in e.friendly_message


def test_dict_unpack_error():
    with pytest.raises(python_evaluator.UserError):
        python_evaluator.exec_input("[(k,v) for (k,v) in {'a': 1}]")


def test_infinite_generator():
    returnInfo = python_evaluator.exec_input(
        """
import itertools
counter = (x for x in itertools.count())
x=next(counter)
    """
    )
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == 0


def test_dont_show_global_vars():
    returnInfo = python_evaluator.exec_input("x = 1", show_global_vars=False)
    assert jsonpickle.decode(returnInfo.userVariables)["zz status"] == "AREPL is configured to not show global vars"


def test_argv0_should_be_file_path():
    code = "from sys import argv;args=argv"
    returnInfo = python_evaluator.exec_input(code)
    assert jsonpickle.decode(returnInfo.userVariables)["args"][0] == ""

    returnInfo = python_evaluator.exec_input(code, "", file_path="test path")
    assert jsonpickle.decode(returnInfo.userVariables)["args"][0] == "test path"


def test_starting_dunders_should_be_correct():
    code = "file_dunder=__file__"
    returnInfo = python_evaluator.exec_input(code)
    assert jsonpickle.decode(returnInfo.userVariables)["file_dunder"] == ""

    returnInfo = python_evaluator.exec_input(code, "", file_path="test path")
    assert jsonpickle.decode(returnInfo.userVariables)["file_dunder"] == "test path"

    returnInfo = python_evaluator.exec_input("name_dunder=__name__")
    assert jsonpickle.decode(returnInfo.userVariables)["name_dunder"] == "__main__"


def test_relative_import():
    file_path = path.join(python_ignore_path, "foo2.py")
    with open(file_path) as f:
        returnInfo = python_evaluator.exec_input(f.read(), "", file_path)
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == 2


def test_jsonpickle_err_doesnt_break_arepl():
    returnInfo = python_evaluator.exec_input(
        """
class foo:
    def __getstate__(self):
        a
f = foo()
    """
    )
    assert jsonpickle.decode(returnInfo.userVariables)["f"] == "AREPL could not pickle this object"


def test_dump():
    returnInfo = python_evaluator.exec_input("from arepl_dump import dump;dump('dump worked');x=1")
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == 1


def test_dump_when_exception():
    # this test prevents rather specific error case where i forget to uncache dump during exception handling
    # and it causes dump to not work properly second time around (see https://github.com/Almenon/AREPL-vscode/issues/91)
    try:
        python_evaluator.exec_input("from arepl_dump import dump;dumpOut = dump('dump worked');x=1;raise Exception()")
    except Exception as e:
        assert "dumpOut" in jsonpickle.decode(e.varsSoFar)
    try:
        python_evaluator.exec_input("from arepl_dump import dump;dumpOut = dump('dump worked');raise Exception()")
    except Exception as e:
        assert "dumpOut" in jsonpickle.decode(e.varsSoFar) and jsonpickle.decode(e.varsSoFar)["dumpOut"] is not None


def test_special_floats():
    returnInfo = python_evaluator.exec_input(
        """
x = float('infinity')
y = float('nan')
z = float('-infinity')
    """
    )
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == "Infinity"
    assert jsonpickle.decode(returnInfo.userVariables)["y"] == "NaN"
    assert jsonpickle.decode(returnInfo.userVariables)["z"] == "-Infinity"


def test_import_does_not_show():
    # we only show local vars to user, no point in showing modules
    returnInfo = python_evaluator.exec_input("import json")
    assert jsonpickle.decode(returnInfo.userVariables) == {}


def test_save():
    returnInfo = python_evaluator.exec_input("", "from random import random\nx=random()#$save")
    randomVal = jsonpickle.decode(returnInfo.userVariables)["x"]
    returnInfo = python_evaluator.exec_input("z=3", "from random import random\nx=random()#$save")
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == randomVal


def test_save_import():  # imports in saved section should be able to be referenced in exec section
    returnInfo = python_evaluator.exec_input("z=math.sin(0)", "import math#$save")
    assert jsonpickle.decode(returnInfo.userVariables)["z"] == 0


def test_various_types():
    various_types = """
a = 1
b = 1.1
c = 'c'
d = (1,2)
def f(x): return x+1
g = {}
h = []
i = [[[]]]
class l():
    def __init__(self,x):
        self.x = x
m = l(5)
n = False

    """
    returnInfo = python_evaluator.exec_input(various_types)

    vars = jsonpickle.decode(returnInfo.userVariables)
    assert vars["a"] == 1
    assert vars["b"] == 1.1
    assert vars["c"] == "c"
    assert vars["d"] == (1, 2)
    assert vars["g"] == {}
    assert vars["h"] == []
    assert vars["i"] == [[[]]]
    assert vars["l"] != None
    assert vars["m"] != None
    assert vars["n"] == False


def test_frame_handler():
    # I have a custom handler for frame (see https://github.com/Almenon/AREPL-backend/issues/26)
    # otherwise frame returns as simply "py/object": "__builtin__.frame"
    frame_code = """
import bdb

f = {}

class areplDebug(bdb.Bdb):
    # override
    def user_line(self,frame):
        global f
        f = frame

b = areplDebug()
b.run('x=1+5',{},{})
    """
    returnInfo = python_evaluator.exec_input(frame_code)
    vars = jsonpickle.decode(returnInfo.userVariables)
    assert vars["f"]["f_lineno"] == 1


def test_generator_handler():
    generator_code = """
def count(start=0):
    while True:
        yield start
        start += 1

counter = count()
    """
    returnInfo = python_evaluator.exec_input(generator_code)
    vars = jsonpickle.decode(returnInfo.userVariables)
    assert vars["counter"]["py/object"] == "builtins.generator"


def test_fileIO():
    fileIO = """
import tempfile

fp = tempfile.TemporaryFile()
fp.write(b'yo')
fp.seek(0)
x = fp.read()
fp.close()
    """
    returnInfo = python_evaluator.exec_input(fileIO)
    vars = jsonpickle.decode(returnInfo.userVariables)
    assert "fp" in vars
    assert vars["x"] == b"yo"


def test_eventLoop():
    eventLoopCode = """
import asyncio

async def async_run():
    pass

def compile_async_tasks():
    tasks = []

    tasks.append(
        asyncio.ensure_future(async_run())
    )
    return tasks

tasks = compile_async_tasks()

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(*tasks))
loop.close()
x=1
    """

    # the async def async_run would result
    # in syntax error in python versions < 3.5
    # so we use different test in that case
    if version_info < (3, 5):
        eventLoopCode = """
import asyncio

@asyncio.coroutine
def hello_world():
    print("Hello World!")

loop = asyncio.get_event_loop()
# Blocking call which returns when the hello_world() coroutine is done
loop.run_until_complete(hello_world())
loop.close()
x=1
    """

    python_evaluator.exec_input(eventLoopCode)
    returnInfo = python_evaluator.exec_input(eventLoopCode)
    vars = jsonpickle.decode(returnInfo.userVariables)
    assert "x" in vars


def test_builtinImportNotDeleted():
    importStr = """
import math
from json import loads
    """
    python_evaluator.exec_input(importStr)
    assert "math" in modules
    assert "json" in modules


def test_pipImportNotDeleted():
    importStr = """
import praw
    """
    python_evaluator.exec_input(importStr)
    assert "praw" in modules
    assert "praw.models.user" in modules


def test_user_import_deleted():

    file_path = path.join(python_ignore_path, "foo.py")
    file_path2 = path.join(python_ignore_path, "foo2.py")

    with open(file_path) as f:
        origFileText = f.read()

    try:
        with open(file_path2) as f:
            returnInfo = python_evaluator.exec_input(f.read(), "", file_path2)
        assert jsonpickle.decode(returnInfo.userVariables)["x"] == 2  # just checking this for later on
        assert "foo" not in modules  # user import should be deleted!

        # now that import is uncached i should be able to change code, rerun & get different result
        with open(file_path, "w") as f:
            f.write("def foo():\n    return 3")

        with open(file_path2) as f:
            returnInfo = python_evaluator.exec_input(f.read(), "", file_path2)
        assert jsonpickle.decode(returnInfo.userVariables)["x"] == 3

    finally:
        # restore file back to original
        with open(file_path, "w") as f:
            f.write(origFileText)


def test_user_var_import_deleted():

    # __pycache__ will muck up our test on every second run
    # this problem only happens during unit tests and not in actual useage (not sure why)
    # so we can safely delete pycache to avoid the problem
    rmtree(path.join(python_ignore_path, "__pycache__"))

    varToImportFile_path = path.join(python_ignore_path, "varToImport.py")
    importVarFile_path = path.join(python_ignore_path, "importVar.py")

    with open(varToImportFile_path) as f:
        origVarToImportFileText = f.read()

    try:
        with open(importVarFile_path) as f:
            returnInfo = python_evaluator.exec_input(f.read(), "", importVarFile_path)
        assert jsonpickle.decode(returnInfo.userVariables)["myVar"] == 5  # just checking this for later on
        assert "varToImport" not in modules  # user import should be deleted!

        # now that import is uncached i should be able to change code, rerun & get different result
        with open(varToImportFile_path, "w") as f:
            f.write("varToImport = 3")

        with open(importVarFile_path) as f:
            returnInfo = python_evaluator.exec_input(f.read(), "", importVarFile_path)
        assert jsonpickle.decode(returnInfo.userVariables)["myVar"] == 3

    finally:
        # restore file back to original
        with open(varToImportFile_path, "w") as f:
            f.write(origVarToImportFileText)


def test_howdoiArepl():
    returnInfo = python_evaluator.exec_input("x=howdoi('use arepl')")
    assert (
        jsonpickle.decode(returnInfo.userVariables)["x"]
        == "using AREPL is simple - just start coding and arepl will show you the final state of your variables. For more help see https://github.com/Almenon/AREPL-vscode/wiki"
    )


def test_script_path_should_work_regardless_of_user_errors():
    try:
        python_evaluator.exec_input("from sys import path;x", file_path=python_ignore_path)
    except python_evaluator.UserError as e:
        returnInfo = e.varsSoFar
    try:
        python_evaluator.exec_input("from sys import path;x", file_path=python_ignore_path)
    except python_evaluator.UserError as e:
        secondReturnInfo = e.varsSoFar

    # script_path should restore the sys path back to original state after execution
    # so each run should have same path
    assert jsonpickle.decode(returnInfo)["path"] == jsonpickle.decode(secondReturnInfo)["path"]


def test_mock_stdin():
    returnInfo = python_evaluator.exec_input("standard_input = 'hello\\nworld';x=input();y=input()")
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == "hello"
    assert jsonpickle.decode(returnInfo.userVariables)["y"] == "world"

    returnInfo = python_evaluator.exec_input("standard_input = ['hello', 'world'];x=input();y=input()")
    assert jsonpickle.decode(returnInfo.userVariables)["x"] == "hello"
    assert jsonpickle.decode(returnInfo.userVariables)["y"] == "world"

    with pytest.raises(python_evaluator.UserError):
        python_evaluator.exec_input("standard_input = ['hello'];x=input();y=input()")


def integration_test_howdoi():
    # this requires internet access so it is not official test
    returnInfo = python_evaluator.exec_input("x=howdoi('eat a apple')")
    print(jsonpickle.decode(returnInfo.userVariables)["x"])  # this should print out howdoi results


###########################
#     WIERD STUFF
###########################

# lambdas do not show up at all

# file objects show up as None

#   class pickling does work with #$save - but not when unit testing for some reason
#   "Can't pickle <class 'python_evaluator.l'>: it's not found as python_evaluator.l"
#   not sure why it's trying to find the class in python_evaluator - it's not going to be there
#   todo: investigate issue

#    def test_can_pickle_class(self):
#         code = """
# class l():
# 	def __init__(self,x):
# 		self.x = x  #$save"""
#         returnInfo = python_evaluator.exec_input("",code)
#         randomVal = jsonpickle.decode(returnInfo['userVariables'])['l']
#         returnInfo = python_evaluator.exec_input("z=3",code)
#         randomVal = jsonpickle.decode(returnInfo['userVariables'])['l']
