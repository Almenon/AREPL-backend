import unittest
import pythonEvaluator
import jsonpickle
from os import getcwd,sep
from sys import version_info

class TestPythonEvaluator(unittest.TestCase):

    def test_simple_code(self):
        returnInfo = pythonEvaluator.exec_input("x = 1")
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == 1

    def test_relative_import(self):
        filePath = getcwd() + sep + "python_ignore" + sep + "foo2.py"
        with open(filePath) as f:
            returnInfo = pythonEvaluator.exec_input(f.read(),"",filePath)
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == 2

    def test_dump(self):
        returnInfo = pythonEvaluator.exec_input("from arepldump import dump;dump('dump worked');x=1")
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == 1

    def test_special_floats(self):
        returnInfo = pythonEvaluator.exec_input("""
x = float('infinity')
y = float('nan')
z = float('-infinity')
        """)
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == "Infinity"
        assert jsonpickle.decode(returnInfo.userVariables)['y'] == "NaN"
        assert jsonpickle.decode(returnInfo.userVariables)['z'] == "-Infinity"

    def test_import_does_not_show(self):
        # we only show local vars to user, no point in showing modules
        returnInfo = pythonEvaluator.exec_input("import json")
        assert jsonpickle.decode(returnInfo.userVariables) == {}

    def test_save(self):
        returnInfo = pythonEvaluator.exec_input("","from random import random\nx=random()#$save")
        randomVal = jsonpickle.decode(returnInfo.userVariables)['x']
        returnInfo = pythonEvaluator.exec_input("z=3","from random import random\nx=random()#$save")
        assert jsonpickle.decode(returnInfo.userVariables)['x'] == randomVal

    def test_import(self): # imports in saved section should be able to be referenced in exec section
        returnInfo = pythonEvaluator.exec_input("z=math.sin(0)","import math#$save")
        assert jsonpickle.decode(returnInfo.userVariables)['z'] == 0

    def test_has_error(self):
        with self.assertRaises(pythonEvaluator.UserError):
            pythonEvaluator.exec_input("x")

    def test_various_types(self):
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
        
        # functions do not show up on decode so we check the json
        assert '"f": {"py/function": "pythonEvaluator.f"}' in returnInfo.userVariables

        vars = jsonpickle.decode(returnInfo.userVariables)
        assert vars['a'] == 1
        assert vars['b'] == 1.1
        assert vars['c'] == 'c'
        assert vars['d'] == (1,2)
        assert vars['g'] == {}
        assert vars['h'] == []
        assert vars['i'] == [[[]]]
        assert vars['l'] != None
        assert vars['m'] != None
        assert vars['n'] == False

    def test_fileIO(self):
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

    def test_eventLoop(self):
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
        if version_info < (3,5):
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

if __name__ == '__main__':
    unittest.main()



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
