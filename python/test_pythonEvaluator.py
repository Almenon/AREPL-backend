import pytest
import pythonEvaluator
import jsonpickle
from os import getcwd, chdir, path, pardir
from sys import version_info,modules
from shutil import rmtree

python_ignore_path = path.join(path.dirname(path.abspath(__file__)), "testDataFiles")


def test_simple_code():
    returnInfo = pythonEvaluator.exec_input("x = 1")
    assert jsonpickle.decode(returnInfo.userVariables)['x'] == 1

def test_argv0ShouldBeFilePath():
    code = "from sys import argv;args=argv"
    returnInfo = pythonEvaluator.exec_input(code)
    assert jsonpickle.decode(returnInfo.userVariables)['args'][0] == ''

    returnInfo = pythonEvaluator.exec_input(code, "", filePath="test path")
    assert jsonpickle.decode(returnInfo.userVariables)['args'][0] == 'test path'

def test_fileDunderShouldHaveRightPath():
    code = "fileDunder=__file__"
    returnInfo = pythonEvaluator.exec_input(code)
    assert jsonpickle.decode(returnInfo.userVariables)['fileDunder'] == ''

    returnInfo = pythonEvaluator.exec_input(code, "", filePath="test path")
    assert jsonpickle.decode(returnInfo.userVariables)['fileDunder'] == 'test path'

def test_relative_import():
    filePath = path.join(python_ignore_path, "foo2.py")
    with open(filePath) as f:
        returnInfo = pythonEvaluator.exec_input(f.read(),"",filePath)
    assert jsonpickle.decode(returnInfo.userVariables)['x'] == 2

def test_dump():
    returnInfo = pythonEvaluator.exec_input("from arepldump import dump;dump('dump worked');x=1")
    assert jsonpickle.decode(returnInfo.userVariables)['x'] == 1

def test_dump_when_exception():
    # this test prevents rather specific error case where i forget to uncache dump during exception handling
    # and it causes dump to not work properly second time around (see https://github.com/Almenon/AREPL-vscode/issues/91)
    try:
        pythonEvaluator.exec_input("from arepldump import dump;dumpOut = dump('dump worked');x=1;raise Exception()")
    except Exception as e:
        assert 'dumpOut' in jsonpickle.decode(e.varsSoFar)
    try:
        pythonEvaluator.exec_input("from arepldump import dump;dumpOut = dump('dump worked');raise Exception()")
    except Exception as e:
        assert 'dumpOut' in jsonpickle.decode(e.varsSoFar) and jsonpickle.decode(e.varsSoFar)['dumpOut'] is not None

def test_special_floats():
    returnInfo = pythonEvaluator.exec_input("""
x = float('infinity')
y = float('nan')
z = float('-infinity')
    """)
    assert jsonpickle.decode(returnInfo.userVariables)['x'] == "Infinity"
    assert jsonpickle.decode(returnInfo.userVariables)['y'] == "NaN"
    assert jsonpickle.decode(returnInfo.userVariables)['z'] == "-Infinity"

def test_import_does_not_show():
    # we only show local vars to user, no point in showing modules
    returnInfo = pythonEvaluator.exec_input("import json")
    assert jsonpickle.decode(returnInfo.userVariables) == {}

def test_save():
    returnInfo = pythonEvaluator.exec_input("","from random import random\nx=random()#$save")
    randomVal = jsonpickle.decode(returnInfo.userVariables)['x']
    returnInfo = pythonEvaluator.exec_input("z=3","from random import random\nx=random()#$save")
    assert jsonpickle.decode(returnInfo.userVariables)['x'] == randomVal

def test_save_import(): # imports in saved section should be able to be referenced in exec section
    returnInfo = pythonEvaluator.exec_input("z=math.sin(0)","import math#$save")
    assert jsonpickle.decode(returnInfo.userVariables)['z'] == 0

def test_has_error():
    with pytest.raises(pythonEvaluator.UserError):
        pythonEvaluator.exec_input("x")

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
    returnInfo = pythonEvaluator.exec_input(various_types)

    vars = jsonpickle.decode(returnInfo.userVariables)
    assert vars['a'] == 1
    assert vars['b'] == 1.1
    assert vars['c'] == 'c'
    assert vars['d'] == (1, 2)
    assert vars['g'] == {}
    assert vars['h'] == []
    assert vars['i'] == [[[]]]
    assert vars['l'] != None
    assert vars['m'] != None
    assert vars['n'] == False

def test_fileIO():
    fileIO = """
import tempfile

fp = tempfile.TemporaryFile()
fp.write(b'yo')
fp.seek(0)
x = fp.read()
fp.close()
    """
    returnInfo = pythonEvaluator.exec_input(fileIO)
    vars = jsonpickle.decode(returnInfo.userVariables)
    assert 'fp' in vars
    assert vars['x'] == b'yo'

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

    pythonEvaluator.exec_input(eventLoopCode)
    returnInfo = pythonEvaluator.exec_input(eventLoopCode)
    vars = jsonpickle.decode(returnInfo.userVariables)
    assert 'x' in vars

def test_ImportNotDeleted():
    importStr = """
import math
from json import loads
    """
    pythonEvaluator.exec_input(importStr)
    assert 'math' in modules
    assert 'json' in modules

def test_userImportDeleted():

    filePath = path.join(python_ignore_path, "foo.py")
    filePath2 = path.join(python_ignore_path, "foo2.py")

    with open(filePath) as f:
        origFileText = f.read()

    try:
        with open(filePath2) as f:
            returnInfo = pythonEvaluator.exec_input(f.read(),"",filePath2)
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == 2 # just checking this for later on
        assert 'foo' not in modules # user import should be deleted!

        # now that import is uncached i should be able to change code, rerun & get different result
        with open(filePath,'w') as f:
            f.write('def foo():\n    return 3')

        with open(filePath2) as f:
            returnInfo = pythonEvaluator.exec_input(f.read(),"",filePath2)
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == 3

    finally:
        # restore file back to original
        with open(filePath, 'w') as f:
            f.write(origFileText)

def test_userVarImportDeleted():

    # __pycache__ will muck up our test on every second run
    # this problem only happens during unit tests and not in actual useage (not sure why)
    # so we can safely delete pycache to avoid the problem
    rmtree(path.join(python_ignore_path, "__pycache__"))

    varToImportFilePath = path.join(python_ignore_path, "varToImport.py")
    importVarFilePath = path.join(python_ignore_path, "importVar.py")

    with open(varToImportFilePath) as f:
        origVarToImportFileText = f.read()

    try:
        with open(importVarFilePath) as f:
            returnInfo = pythonEvaluator.exec_input(f.read(),"",importVarFilePath)
        assert jsonpickle.decode(returnInfo.userVariables)['myVar'] == 5 # just checking this for later on
        assert 'varToImport' not in modules # user import should be deleted!

        # now that import is uncached i should be able to change code, rerun & get different result
        with open(varToImportFilePath,'w') as f:
            f.write('varToImport = 3')

        with open(importVarFilePath) as f:
            returnInfo = pythonEvaluator.exec_input(f.read(),"",importVarFilePath)
        assert jsonpickle.decode(returnInfo.userVariables)['myVar'] == 3

    finally:
        # restore file back to original
        with open(varToImportFilePath, 'w') as f:
            f.write(origVarToImportFileText)


###########################
#     WIERD STUFF
###########################

# lambdas do not show up at all

# file objects show up as None

#   class pickling does work with #$save - but not when unit testing for some reason
#   "Can't pickle <class 'pythonEvaluator.l'>: it's not found as pythonEvaluator.l"
#   not sure why it's trying to find the class in pythonEvaluator - it's not going to be there
#   todo: investigate issue

#    def test_can_pickle_class(self):
#         code = """
# class l():
# 	def __init__(self,x):
# 		self.x = x  #$save"""
#         returnInfo = pythonEvaluator.exec_input("",code)
#         randomVal = jsonpickle.decode(returnInfo['userVariables'])['l']
#         returnInfo = pythonEvaluator.exec_input("z=3",code)
#         randomVal = jsonpickle.decode(returnInfo['userVariables'])['l']
