from pickler import pickle_user_vars
from traceback import TracebackException

class UserError(Exception):
    """
    user errors should be caught and re-thrown with this
    Be warned that this exception can throw an exception.  Yes, you read that right.  I apologize in advance.
    :raises: ValueError (varsSoFar gets pickled into JSON, which may result in any number of errors depending on what types are inside)
    """

    def __init__(self, exc_obj, exc_tb, varsSoFar={}, execTime=0):
        self.traceback_exception = TracebackException(type(exc_obj), exc_obj, exc_tb, limit=100)
        self.varsSoFar = pickle_user_vars(varsSoFar)
        self.execTime = execTime