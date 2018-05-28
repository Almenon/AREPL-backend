import unittest
from arepl import dump,identifier
from json import loads

class TestPythonEvaluator(unittest.TestCase):

    def parse_output(self, output):
        output = output.replace(identifier,'',1)
        return loads(output)

    def test_simple_dump(self):
        x = self.parse_output(dump('yo'))
        assert x['test_simple_dump']['dump output'] == 'yo'

    def test_dump_all_vars(self):
        y = 'hey'
        x = self.parse_output(dump())
        assert x['test_dump_all_vars']['y'] == 'hey'

    def test_dump_at(self):
        for i in range(10):
            output = dump("yo")
            output2 = dump(i,3)
            if i is 0:
                output = self.parse_output(output)
                assert output['test_dump_at']['dump output'] == "yo"
            elif i is 3:
                output2 = self.parse_output(output2)
                assert output2['test_dump_at']['dump output'] == 3
            else:
                assert output is None

if __name__ == '__main__':
    unittest.main()
