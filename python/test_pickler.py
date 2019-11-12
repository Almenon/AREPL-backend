from pickler import specialVars, pickle_user_vars, pickle_user_error
import python_evaluator

def test_error_has_extended_traceback_1():
    try:
        python_evaluator.exec_input("""
try:
    x
except NameError as e:
    x=1/0
""")
    except (KeyboardInterrupt, SystemExit):
        raise
    except python_evaluator.UserError as e:
        json = pickle_user_error(e.traceback_exception)
        assert "ZeroDivisionError" in json
        assert "NameError" in json

def test_error_has_extended_traceback_2():
    try:
        python_evaluator.exec_input("""
def foo():
    raise ZeroDivisionError()
    
try:
    foo()
except Exception as e:
    fah
""")
    except (KeyboardInterrupt, SystemExit):
        raise
    except python_evaluator.UserError as e:
        json = pickle_user_error(e.traceback_exception)
        assert "NameError" in json
        assert "ZeroDivisionError" in json