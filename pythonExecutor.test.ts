/*global suite, test*/ //comment for eslint

// This test uses TDD Mocha. see https://mochajs.org/ for help
// http://ricostacruz.com/cheatsheets/mocha-tdd

// The module 'assert' provides assertion methods from node
import * as assert from 'assert'

import { PythonExecutor, PythonState } from './pythonExecutor'
import { EOL } from 'os';

function isEmpty(obj) {
    return Object.keys(obj).length === 0;
}

suite("python_evaluator Tests", () => {
    let pyEvaluator = new PythonExecutor()
    let input = {
        evalCode: "",
        filePath: "",
        usePreviousVariables: false,
        show_global_vars: true,
        default_filter_vars: [],
        default_filter_types: ["<class 'module'>", "<class 'function'>"]
    }
    const pythonStartupTime = 3000

    suiteSetup(function () {
        this.timeout(pythonStartupTime + 500)
    })

    setup(function (done) {
        pyEvaluator.onPrint = () => { }
        pyEvaluator.onStderr = () => { }
        pyEvaluator.onResult = () => { }
        pyEvaluator.start(done)
    })

    teardown(function(){
        pyEvaluator.stop(true)
    })

    test("sanity check: 1+1=2", () => {
        assert.strictEqual(1 + 1, 2)
    })

    test("returns result", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.notStrictEqual(result, null)
            done()
        }
        pyEvaluator.onStderr = (err: string) => {
            done(err)
        }
        pyEvaluator.onPrint = (msg: string) => {
            done(msg)
        }
        input.evalCode = "x"
        pyEvaluator.execCode(input)
    })

    test("returns user variables", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.strictEqual(result.userVariables['x'], 1)
            done()
        }
        input.evalCode = "x=1"
        pyEvaluator.execCode(input)
    })

    test("can import importlib", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.strictEqual(result.userErrorMsg, undefined)
            done()
        }
        input.evalCode = "import importlib.resources as rsrc"
        pyEvaluator.execCode(input)
    })

    test("returns user variables properly when there is a lot of content", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.strictEqual(result.userVariables['x'], 1)
            done()
        }
        input.evalCode = "x=1;y='a'*80000"
        pyEvaluator.execCode(input)
    })

    suite("stdout/stderr tests", () => {

        test("can print stdout", function (done) {
            let hasPrinted = false
            pyEvaluator.onPrint = (stdout) => {
                assert.strictEqual(stdout, "hello world" + EOL)
                hasPrinted = true
            }

            pyEvaluator.onResult = () => {
                if (!hasPrinted) assert.fail("program has returned result", "program should still be printing")
                else done()
            }

            input.evalCode = "print('hello world')"
            pyEvaluator.execCode(input)
        })

        test("can print stdout if no newline", function (done) {
            let hasPrinted = false
            pyEvaluator.onPrint = (stdout) => {
                assert.strictEqual(stdout, "hello world")
                hasPrinted = true
            }

            pyEvaluator.onResult = () => {
                if (!hasPrinted) assert.fail("program has returned result", "program should still be printing")
                else done()
            }

            input.evalCode = "print('hello world', end='')"
            pyEvaluator.execCode(input)
        })

        test("can print stderr", function (done) {
            let hasLogged = false
            pyEvaluator.onStderr = (stderr) => {
                assert.strictEqual(stderr, "hello world")
                hasLogged = true
                done()
            }

            pyEvaluator.onResult = (result) => {
                setTimeout(() => {
                    if (!hasLogged) assert.fail("program has returned result " + JSON.stringify(result), "program should still be logging")
                }, 100); //to avoid race conditions wait a bit in case stderr arrives later
            }

            input.evalCode = "import sys;sys.stderr.write('hello world')"
            pyEvaluator.execCode(input)
        })

        test("can print multiple lines", function (done) {
            let firstPrint = false

            pyEvaluator.onPrint = (stdout) => {
                // not sure why it is doing this.. stdout should be line buffered
                // so we should get 1 and 2 seperately
                assert.strictEqual(stdout, '1' + EOL + '2' + EOL)
                firstPrint = true
            }

            pyEvaluator.onResult = () => {
                if (!firstPrint) assert.fail("program has returned result", "program should still be printing")
                else done()
            }

            input.evalCode = "[print(x) for x in [1,2]]"
            pyEvaluator.execCode(input)
        })

        test("prints in real-time", function (done) {
            let printed = false

            pyEvaluator.onPrint = (stdout) => { printed = true }
            pyEvaluator.onResult = () => { done() }

            setTimeout(() => { if (!printed) assert.fail("") }, 25)

            input.evalCode = "from time import sleep\nprint('a')\nsleep(.05)\nprint(b)"
            pyEvaluator.execCode(input)
        })

        test("returns result after print", function (done) {
            pyEvaluator.onPrint = (stdout) => {
                assert.strictEqual(stdout, "hello world" + EOL)
                assert.strictEqual(pyEvaluator.state, PythonState.Executing)
            }

            pyEvaluator.onResult = () => {
                assert.strictEqual(pyEvaluator.state, PythonState.DirtyFree)
                done()
            }

            input.evalCode = "print('hello world')"
            pyEvaluator.execCode(input)
        })
    })

    test("no encoding errors with utf8 on windows", function (done) {
        // other platforms may have the locale encoding
        // so we just test windows
        // see https://docs.python.org/3/library/sys.html#sys.stdout
        if (process.platform != "win32") {
            done()
            return
        }
        pyEvaluator.onResult = (result) => {
            assert.strictEqual(result.userErrorMsg, undefined)
            assert.strictEqual(result.internalError, null)
            done()
        }
        input.evalCode = "#㍦"
        pyEvaluator.execCode(input)
    })

    test("dump returns result", function (done) {
        let gotDump = false
        pyEvaluator.onResult = (result) => {
            if (gotDump) return
            assert.notStrictEqual(result, null)
            assert.strictEqual(isEmpty(result.userError), true)
            assert.strictEqual(result.internalError, null)
            assert.strictEqual(result.userVariables['dump output'], 5)
            assert.strictEqual(result.caller, '<module>')
            assert.strictEqual(result.lineno, 1)
            gotDump = true
            done()
        }
        input.evalCode = "from arepl_dump import dump;dump(5)"
        pyEvaluator.execCode(input)
    })

    test("returns syntax error when incorrect syntax", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.notStrictEqual(result.userError, null)
            assert.strictEqual(result.userError.filename, '<string>')
            assert.strictEqual(result.userError.lineno, '1')
            assert.strictEqual(result.userError.msg, 'invalid syntax')
            done()
        }
        input.evalCode = "x="
        pyEvaluator.execCode(input)
    })

    test("uses previousRun variables asked", function (done) {
        function onSecondResult(result) {
            assert.strictEqual(result.userVariables['y'], 1)
            done()
        }
        pyEvaluator.onResult = (result) => {
            pyEvaluator.onResult = onSecondResult
            input.usePreviousVariables = true
            pyEvaluator.execCode(input)
            input.usePreviousVariables = false
        }
        input.evalCode = "x=1"
        pyEvaluator.execCode(input)
        input.evalCode = "y=x"
    })

    test("can restart", function (done) {

        this.timeout(this.timeout() + pythonStartupTime)

        assert.strictEqual(pyEvaluator.state, PythonState.FreshFree)

        pyEvaluator.restart(() => {
            assert.strictEqual(pyEvaluator.state, PythonState.FreshFree)
            pyEvaluator.onResult = () => done()
            input.evalCode = "x"
            pyEvaluator.execCode(input)
        })
    })

    test("strips out unnecessary error info", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.strictEqual(result.userErrorMsg, "Traceback (most recent call last):\n  line 1, in <module>\nNameError: name 'x' is not defined\n")
            done()
        }
        input.evalCode = "x"
        pyEvaluator.execCode(input)
    })

    test("strips out unnecessary error info even with long tracebacks", function (done) {
        pyEvaluator.onResult = (result) => {
            // asserting the exact string would result in flaky tests
            // because internal python code could change & the traceback would be different
            // so we just do some generic checks
            assert.strictEqual(result.userErrorMsg.includes("TypeError"), true)
            assert.strictEqual(result.userErrorMsg.split('File ').length > 1, true)
            assert.strictEqual(result.userErrorMsg.includes("python_evaluator.py"), false)
            assert.strictEqual(result.userErrorMsg.includes("exec(data['evalCode'], evalLocals)"), false)
            done()
        }
        input.evalCode = "import json;json.dumps(json)"
        pyEvaluator.execCode(input)
    })

    test("strips out unnecessary error info even with multiple tracebacks", function (done) {
        pyEvaluator.onResult = (result) => {
            assert.strictEqual(result.userErrorMsg, `Traceback (most recent call last):
  line 6, in <module>
  line 3, in foo
Exception

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  line 8, in <module>
NameError: name 'fah' is not defined
`)
            done()
        }

        input.evalCode = `
def foo():
    raise Exception
    
try:
    foo()
except Exception as e:
    fah`

        pyEvaluator.execCode(input)
    })

    test("checks syntax", function (done) {
        pyEvaluator.checkSyntax("x=").then(() => {
            assert.fail("promise should have been rejected")
        }).catch(() => { })

        pyEvaluator.checkSyntax("x=1").then(() => {
            done()
        }).catch((err) => {
            assert.fail("syntax was correct there should not have been an error")
        })
    })

})
