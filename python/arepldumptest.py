import unittest
from arepldump import dump
from json import loads

# this test has to be in main scope
# so we cant run it inside a function
output = dump(5)


class TestPythonEvaluator(unittest.TestCase):
    def test_simple_dump(self):
        dumpInfo = dump('yo')
        assert loads(dumpInfo.userVariables)['dump output'] == 'yo'
        assert dumpInfo.caller == 'test_simple_dump'
        assert dumpInfo.done == False

    def test_dump_main_scope(self):
        global output
        assert loads(output.userVariables)['dump output'] == 5
        assert output.caller == '<module>'

    def test_dump_all_vars(self):
        y = 'hey'
        dumpInfo = dump()
        assert loads(dumpInfo.userVariables)['y'] == 'hey'

    def test_dump_at(self):
        for i in range(10):
            output = dump('yo')
            output2 = dump(i, 3)
            if i is 0:
                output = output
                assert loads(output.userVariables)['dump output'] == 'yo'
            elif i is 3:
                output2 = output2
                assert loads(output2.userVariables)['dump output'] == 3
            else:
                assert output is None


if __name__ == '__main__':
    unittest.main()
