from pickler import pickle_user_vars

class UserError(Exception):
    """
    user errors should be caught and re-thrown with this
    Be warned that this exception can throw an exception.  Yes, you read that right.  I apolagize in advance.
    :raises: ValueError (varsSoFar gets pickled into JSON, which may result in any number of errors depending on what types are inside)
    """

    def __init__(self, message, varsSoFar={}, execTime=0):
        super().__init__(message)
        self.varsSoFar = pickle_user_vars(varsSoFar)
        self.execTime = execTime