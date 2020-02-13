from pickler import specialVars, pickle_user_vars, pickle_user_error
import python_evaluator
import jsonpickle


def test_jsonpickle_err_doesnt_break_arepl():
    class foo:
        def __getstate__(self):
            a
    f = foo()

    assert jsonpickle.decode(pickle_user_vars(locals()))["f"] == "AREPL could not pickle this object"

# I don't want to require pandas to run tests
# So leaving this commented, devs can uncomment to run test if they want to
# def test_jsonpickle_err_doesnt_break_arepl_2():
#     import pandas as pd
#     lets = ['A', 'B', 'C']
#     nums = ['1', '2', '3']
#     midx = pd.MultiIndex.from_product([lets, nums])
#     units = pd.Series(0, index=midx)

#     assert jsonpickle.decode(pickle_user_vars(locals()))["units"] == "AREPL could not pickle this object"


def test_error_has_extended_traceback_1():
    try:
        python_evaluator.exec_input(
            """
try:
    x
except NameError as e:
    x=1/0
"""
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except python_evaluator.UserError as e:
        json = pickle_user_error(e.traceback_exception)
        assert "ZeroDivisionError" in json
        assert "NameError" in json


def test_error_has_extended_traceback_2():
    try:
        python_evaluator.exec_input(
            """
def foo():
    raise ZeroDivisionError()
    
try:
    foo()
except Exception as e:
    fah
"""
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except python_evaluator.UserError as e:
        json = pickle_user_error(e.traceback_exception)
        assert "NameError" in json
        assert "ZeroDivisionError" in json
