import re
import datetime
import decimal
from jsonpickle.handlers import BaseHandler
from types import FrameType
from types import CodeType
from os import DirEntry

NOT_SERIALIZABLE_MESSAGE = "not serializable by arepl"

class DatetimeHandler(BaseHandler):
    ### better represention of datetime, see https://github.com/jsonpickle/jsonpickle/issues/109 ###
    def flatten(self, obj, data):
        x = {"date/time": str(obj)}
        return x

class DecimalHandler(BaseHandler):
    def flatten(self, obj, data):
        x = float(obj)
        return x

class DirEntryHandler(BaseHandler):
    def flatten(self, obj, data):
        return {
            "py/object": "nt.DirEntry",
            "name": obj.name,
            "path": obj.path
        }

class regexMatchHandler(BaseHandler):
    ### better represention of datetime, see https://github.com/jsonpickle/jsonpickle/issues/109 ###
    def flatten(self, obj, data):
        return {
            "py/object": "_sre.SRE_Match",
            "match": obj.group(0),
            "groups": obj.groups(),
            "span": obj.span(),
        }


class frameHandler(BaseHandler):
    ### better represention of frame, see https://github.com/Almenon/AREPL-backend/issues/26 ###
    def flatten(self, obj, data):
        if obj is None: return None
        return {
            "py/object": "types.FrameType",
            "f_back": self.flatten(obj.f_back, data),
            "f_builtins": NOT_SERIALIZABLE_MESSAGE,
            "f_code": codeHandler(None).flatten(obj.f_code, data),
            "f_globals": NOT_SERIALIZABLE_MESSAGE,
            "f_lasti": obj.f_lasti,
            "f_lineno": obj.f_lineno,
            "f_locals": NOT_SERIALIZABLE_MESSAGE
        }

    def restore(self, obj):
        """just for unit testing"""
        return obj

class codeHandler(BaseHandler):
    ### better represention of frame, see https://github.com/Almenon/AREPL-backend/issues/26 ###
    def flatten(self, obj, data):
        return {
            'co_argcount': obj.co_argcount,
            'co_code': NOT_SERIALIZABLE_MESSAGE,
            'co_cellvars': obj.co_cellvars,
            'co_consts': NOT_SERIALIZABLE_MESSAGE,
            'co_filename': obj.co_filename,
            'co_firstlineno': obj.co_firstlineno,
            'co_flags': obj.co_flags,
            'co_lnotab': NOT_SERIALIZABLE_MESSAGE,
            'co_freevars': NOT_SERIALIZABLE_MESSAGE,
            'co_kwonlyargcount': obj.co_kwonlyargcount,
            'co_name': obj.co_name,
            'co_names': obj.co_names,
            'co_nlocals': NOT_SERIALIZABLE_MESSAGE,
            'co_stacksize': obj.co_stacksize,
            'co_varnames': obj.co_varnames
        }

handlers = [
    {'type': datetime.date, 'handler': DatetimeHandler},
    {'type': datetime.time, 'handler': DatetimeHandler},
    {'type': datetime.datetime, 'handler': DatetimeHandler},
    {'type': type(re.search('', '')), 'handler': regexMatchHandler},
    {'type': FrameType, 'handler': frameHandler},
    {'type': CodeType, 'handler': codeHandler},
    {'type': decimal.Decimal, 'handler': DecimalHandler},
    {'type': DirEntry, 'handler': DirEntryHandler}
]
