import pytest
from json import loads

from arepl_dump import dump

# this test has to be in main scope
# so we cant run it inside a function
output = dump(5)


def test_simple_dump():
    dumpInfo = dump("yo")
    assert loads(dumpInfo.userVariables)["dump output"] == "yo"
    assert dumpInfo.caller == "test_simple_dump"
    assert dumpInfo.done == False


def test_dump_main_scope():
    global output
    assert loads(output.userVariables)["dump output"] == 5
    assert output.caller == "<module>"


def test_dump_all_vars():
    y = "hey"
    dumpInfo = dump()
    assert loads(dumpInfo.userVariables)["y"] == "hey"


def test_dump_at():
    for i in range(10):
        output = dump("yo")
        output2 = dump(i, 3)
        if i == 0:
            output = output
            assert loads(output.userVariables)["dump output"] == "yo"
        elif i == 3:
            output2 = output2
            assert loads(output2.userVariables)["dump output"] == 3
        else:
            assert output is None


def test_dump_at_list():
    for i in range(10):
        output = dump(i, [2, 3])
        if i == 2:
            output = output
            assert loads(output.userVariables)["dump output"] == 2
        elif i == 3:
            output = output
            assert loads(output.userVariables)["dump output"] == 3
        else:
            assert output is None


# This test fails but not sure how to fix it
# I don't know of any easy way to make dump work with single line
# def test_dump_same_line():
#     # fmt: off
#     dumpInfo = dump(1);dumpInfo2 = dump(2)
#     # fmt: on

#     assert loads(dumpInfo.userVariables)["dump output"] == 1
#     assert dumpInfo.caller == "test_dump_same_line"
#     assert dumpInfo.done == False

#     assert loads(dumpInfo2.userVariables)["dump output"] == 2
#     assert dumpInfo2.caller == "test_dump_same_line"
#     assert dumpInfo2.done == False
