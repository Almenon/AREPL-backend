from importlib import util #https://stackoverflow.com/questions/39660934/error-when-using-importlib-util-to-check-for-library
from math import isnan
import jsonpickle
from custom_handlers import handlers

#####################################
"""
This file sets up jsonpickle. Jsonpickle is used in pickle_user_vars for picking user variables.
"""
#####################################

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

specialVars = ['__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__', 'areplStore']

def pickle_user_vars(userVars):

    # filter out non-user vars, no point in showing them
    userVariables = {k:v for k,v in userVars.items() if str(type(v)) != "<class 'module'>"
                     and str(type(v)) != "<class 'function'>"
                     and k not in specialVars+['__builtins__']}

    # but we do want to show areplStore if it has data
    if userVars.get('areplStore') is not None:
        userVariables['areplStore'] = userVars['areplStore']


    # json dumps cant handle any object type, so we need to use jsonpickle
    # still has limitations but can handle much more
    return jsonpickle.encode(userVariables, 
        max_depth=100, # any depth above 245 resuls in error and anything above 100 takes too long to process
        fail_safe=lambda x:"AREPL could not pickle this object"
    ) 
