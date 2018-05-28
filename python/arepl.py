import jsonpickle # import my custom jsonpickle here
import inspect
import json
from pythonEvaluator import pickle_user_vars

identifier = "6q3co5"

context = {}

def dump(variable=None,atCount=0):
    """
    dumps specified var to arepl viewer or all vars of calling func if unspecified
    atCount: when to dump. ex: dump(,3) to dump vars at fourth iteration of loop
    """

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
            returnInfo = callingFrame.f_locals
        else:
            returnInfo = {'dump output': variable}


        # print output
        returnInfo = {caller: returnInfo}
        returnJsonStr = pickle_user_vars(returnInfo)
        print(identifier+returnJsonStr)
        
        # we don't need to return anything for user, this is just to make testing easier
        return identifier+returnJsonStr