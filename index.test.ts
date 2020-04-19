/*global suite, test*/ //comment for eslint

// This test uses TDD Mocha. see https://mochajs.org/ for help
// http://ricostacruz.com/cheatsheets/mocha-tdd

// The module 'assert' provides assertion methods from node
import * as assert from 'assert'

import {PythonEvaluator} from './index'

function isEmpty(obj) {
    return Object.keys(obj).length === 0;
}

suite("python_evaluator Tests", () => {
    let pyEvaluator = new PythonEvaluator()
    let input = {
      evalCode:"",
      savedCode: "",
      filePath: "",
      usePreviousVariables: false,
      showGlobalVars: true,
      default_filter_vars: [],
      default_filter_types: ["<class 'module'>", "<class 'function'>"]
    }
    const pythonStartupTime = 3500
    // python 3.7 has much faster startup time
    // when we drop support for 3.6 we can decrease this

    suiteSetup(function(done){
        this.timeout(pythonStartupTime+500)
        pyEvaluator.start()
        // wait for for python to start
        setTimeout(()=>done(), pythonStartupTime)
    })

    test("sanity check: 1+1=2", () => {
        assert.equal(1+1,2)
    })

    test("returns result", function(done){
        pyEvaluator.onResult = (result)=>{
            assert.notEqual(result, null)
            done()
        }
        input.evalCode = "x"
        pyEvaluator.execCode(input)
    })

    test("arepl_store works", function(done){
        pyEvaluator.onPrint = (result)=>{
            assert.strictEqual(result, "3")
        }

        input.evalCode = "arepl_store=3"
        pyEvaluator.onResult = ()=>{}
        pyEvaluator.execCode(input)

        let onSecondRun = false
        pyEvaluator.onResult = (result)=>{
            if(result.userErrorMsg){
                done(result.userErrorMsg)
            }
            else if(!onSecondRun){
                input.evalCode = "print(arepl_store)"
                pyEvaluator.execCode(input)
                onSecondRun = true
            }
            else{
                done()
            }
        }
    })

    // todo: FIX THIS!
    // test("no encoding errors with utf16", function(done){
    //     pyEvaluator.onResult = (result)=>{
    //         assert.equal(result.userError, '')
    //         assert.equal(result.internalError, null)
    //         done()
    //     }
    //     input.evalCode = "#㍦"
    //     pyEvaluator.execCode(input)
    // })

    test("dump returns result", function(done){
        let gotDump = false
        pyEvaluator.onResult = (result)=>{
            if(gotDump) return
            assert.notEqual(result, null)
            assert.equal(isEmpty(result.userError), true)
            assert.equal(result.internalError, null)
            assert.equal(result.userVariables['dump output'], 5)
            assert.equal(result.caller, '<module>')
            assert.equal(result.lineno, 1)
            gotDump = true
            done()
        }
        input.evalCode = "from arepl_dump import dump;dump(5)"
        pyEvaluator.execCode(input)
    })

    test("returns syntax error when incorrect syntax", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.notEqual(result.userError, null)
            assert.equal(result.userError.filename, '<string>')
            assert.equal(result.userError.lineno, '1')
            assert.equal(result.userError.msg, 'invalid syntax')
            done()
        }
        input.evalCode = "x="
        pyEvaluator.execCode(input)
    })

    test("returns user variables", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.equal(result.userVariables['x'], 1)
            done()
        }
        input.evalCode = "x=1"
        pyEvaluator.execCode(input)
    })

    test("uses previousRun variables asked", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.equal(result.userVariables['y'], 1)
            done()
        }
        input.evalCode = "y=x"
        input.usePreviousVariables = true
        pyEvaluator.execCode(input)
        input.usePreviousVariables = false
    })

    test("can print stdout", function(done){
        let hasPrinted = false
        pyEvaluator.onPrint = (stdout)=>{ 
            assert.equal(stdout, "hello world")
            hasPrinted = true
        }

        pyEvaluator.onResult = () => {
            if(!hasPrinted) assert.fail("program has returned result","program should still be printing")
            else done()
        }

        input.evalCode = "print('hello world')"
        pyEvaluator.execCode(input)
    })

    test("can print stderr", function(done){
        let hasLogged = false
        pyEvaluator.onStderr = (stderr)=>{ 
            assert.equal(stderr, "hello world\r")
            // I have nooo clue why the \r is at the end
            // for some reason python-shell recieves hello world\r\r\n
            hasLogged = true
        }

        pyEvaluator.onResult = (result) => {
            if(!hasLogged) assert.fail("program has returned result","program should still be logging")
            else done()
        }

        input.evalCode = "import sys;sys.stderr.write('hello world\\r\\n')"
        pyEvaluator.execCode(input)
    })

    test("can print multiple lines", function(done){
        let firstPrint = false
        let secondPrint = false

        pyEvaluator.onPrint = (stdout)=>{ 
            if(firstPrint){
                assert.equal(stdout, '2')
                secondPrint = true
            }
            else{
                assert.equal(stdout, "1")
                firstPrint = true
            }
        }

        pyEvaluator.onResult = () => {
            if(!secondPrint) assert.fail("program has returned result","program should still be printing")
            else done()
        }

        input.evalCode = "[print(x) for x in [1,2]]"
        pyEvaluator.execCode(input)
    })

    test("returns result after print", function(done){
        pyEvaluator.onPrint = (stdout)=>{ 
            assert.equal(stdout, "hello world")
            assert.equal(pyEvaluator.executing, true)
        }

        pyEvaluator.onResult = () => {
            assert.equal(pyEvaluator.executing, false)
            done()
        }

        input.evalCode = "print('hello world')"
        pyEvaluator.execCode(input)
    })

    test("can restart", function(done){

        this.timeout(this.timeout()+pythonStartupTime)

        assert.equal(pyEvaluator.running, true)
        assert.equal(pyEvaluator.restarting, false)
        assert.equal(pyEvaluator.executing, false)

        pyEvaluator.restart(()=>{
            assert.equal(pyEvaluator.running, true)
            assert.equal(pyEvaluator.executing, false)

            setTimeout(()=>{
                // by now python should be restarted and accepting input
                pyEvaluator.onResult = ()=>done()
                input.evalCode = "x"
                pyEvaluator.execCode(input)
            },1500)
        })
    })

    test("strips out unnecessary error info", function(done){
        pyEvaluator.onResult = (result)=>{
            assert.equal(result.userErrorMsg, "Traceback (most recent call last):\n  line 1, in <module>\nNameError: name 'x' is not defined\n")
            done()
        }
        input.evalCode = "x"
        pyEvaluator.execCode(input)
    })

    test("strips out unnecessary error info even with long tracebacks", function(done){
        pyEvaluator.onResult = (result)=>{
            // asserting the exact string would result in flaky tests
            // because internal python code could change & the traceback would be different
            // so we just do some generic checks
            assert.equal(result.userErrorMsg.includes("TypeError"), true)
            assert.equal(result.userErrorMsg.split('File ').length > 1, true)
            assert.equal(result.userErrorMsg.includes("python_evaluator.py"), false)
            assert.equal(result.userErrorMsg.includes("exec(data['evalCode'], evalLocals)"), false)
            done()
        }
        input.evalCode = "import json;json.dumps(json)"
        pyEvaluator.execCode(input)
    })

    test("strips out unnecessary error info even with multiple tracebacks", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.equal(result.userErrorMsg, `Traceback (most recent call last):
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

    test("prints in real-time", function(done){
        let printed = false

        pyEvaluator.onPrint = (stdout)=>{ printed = true }
        pyEvaluator.onResult = () => { done() }

        setTimeout(()=>{ if(!printed) assert.fail("") }, 25)

        input.evalCode = "from time import sleep\nprint('a')\nsleep(.05)\nprint(b)"
        pyEvaluator.execCode(input)
    })

    test("checks syntax", function(done){
        pyEvaluator.checkSyntax("x=").then(()=>{
            assert.fail("promise should have been rejected")
        }).catch(()=>{})

        pyEvaluator.checkSyntax("x=1").then(()=>{
            done()
        }).catch((err)=>{
            assert.fail("syntax was correct there should not have been an error")
        })
    })

})
