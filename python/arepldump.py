import jsonpickle
import inspect
import json
from time import time
from pythonEvaluator import pickle_user_vars, returnInfo, print_output

context = {}

def dump(variable=None,atCount=0):
    """
    dumps specified var to arepl viewer or all vars of calling func if unspecified
    atCount: when to dump. ex: dump(,3) to dump vars at fourth iteration of loop
    """
    startTime = time()

    callingFrame = inspect.currentframe().f_back

    callerFile = callingFrame.f_code.co_filename 
    callerLine = callingFrame.f_lineno
    caller = callingFrame.f_code.co_name
    key = callerFile+caller+str(callerLine)

    count = 0

    try:
        count = context[key]+1
    except KeyError:
        pass

    context[key] = count

    if count == atCount:
        if variable is None:
            variableDict = callingFrame.f_locals
        else:
            variableDict = {'dump output': variable}

        variableJson = pickle_user_vars(variableDict)
        myReturnInfo = returnInfo("", variableJson, -1, time()-startTime, None, caller, callerLine, done=False)

        print_output(myReturnInfo)
        
        # we don't need to return anything for user, this is just to make testing easier
        return myReturnInfo

# dump(5) for quick testing