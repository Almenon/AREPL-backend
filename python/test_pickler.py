from pickler import specialVars, pickle_user_vars, pickle_user_error
import python_evaluator

def test_error_has_traceback():
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
        json = pickle_user_error(e)
        assert "NameError" in json