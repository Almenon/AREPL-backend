import arepl_jsonpickle as jsonpickle

import arepl_python_evaluator as python_evaluator


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
    return_info = python_evaluator.exec_input(python_evaluator.ExecArgs(frame_code))
    vars = jsonpickle.decode(return_info.userVariables)
    # todo: assert == 1 once python 3.12.8 is released
    # (see https://github.com/python/cpython/issues/125422)
    assert type(vars["f"]["f_lineno"]) is int


def test_generator_handler():
    generator_code = """
def count(start=0):
    while True:
        yield start
        start += 1

counter = count()
    """
    return_info = python_evaluator.exec_input(python_evaluator.ExecArgs(generator_code))
    vars = jsonpickle.decode(return_info.userVariables)
    assert vars["counter"]["py/object"] == "builtins.generator"


def test_textio_handler():
    generator_code = """
with open(__file__, encoding='cp1252') as f:
    pass
    """
    return_info = python_evaluator.exec_input(python_evaluator.ExecArgs(generator_code, "", __file__))
    assert (
        '"f": {"py/object": "_io.TextIOWrapper", "write_through": false, "line_buffering": false, "errors": "strict", "encoding": "cp1252", "mode": "r"}'
        in return_info.userVariables
    )
