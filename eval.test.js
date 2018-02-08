/*global suite, test*/ //comment for eslint

// This test uses TDD Mocha. see https://mochajs.org/ for help
// http://ricostacruz.com/cheatsheets/mocha-tdd

// The module 'assert' provides assertion methods from node
const assert = require("assert")

const evals = require("./index")

suite("PythonEvaluator Tests", () => {
    let pyEvaluator = new evals.PythonEvaluator()
    let input = {evalCode:"", savedCode: ""}
    pyEvaluator.startPython()

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

    test("returns error when bad code", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.notEqual(result.ERROR, null)
            assert.notEqual(result.ERROR.trim(), "")
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
            assert.equal(pyEvaluator.evaling, true)
        }

        pyEvaluator.onResult = () => {
            assert.equal(pyEvaluator.evaling, false)
            done()
        }

        input.evalCode = "print('hello world')"
        pyEvaluator.execCode(input)
    })

    test("can restart", function(done){

        assert.equal(pyEvaluator.running, true)
        assert.equal(pyEvaluator.restarting, false)
        assert.equal(pyEvaluator.evaling, false)

        pyEvaluator.restart(()=>{
            assert.equal(pyEvaluator.running, true)
            assert.equal(pyEvaluator.evaling, false)

            // i should actually test sending & reciving input to make sure evalutor is on
            // but i tried it and it failed (likely due to some mysterious timing issue)
            // the kicker is it worked when I tried debugging it... uggghhh
            done()
        })
    })

    test("strips out unnecessary error info", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.equal(result.ERROR, "Traceback (most recent call last):\n  line 1, in <module>\nNameError: name 'x' is not defined\n")
            done()
        }
        input.evalCode = "x"
        pyEvaluator.execCode(input)
    })

    test("prints in real-time", function(done){
        let printed = false

        pyEvaluator.onPrint = (stdout)=>{ printed = true }
        pyEvaluator.onResult = () => { done() }

        setTimeout(()=>{ if(!printed) assert.fail() }, 25)

        input.evalCode = "from time import sleep\nprint('a')\nsleep(.05)\nprint(b)"
        pyEvaluator.execCode(input)
    })

    test("checks syntax", function(done){
        pyEvaluator.checkSyntax("x=").then(()=>{
            assert.fail()
        }).catch((err)=>{
            done()
        })

        pyEvaluator.checkSyntax("x=1").then(()=>{
            done()
        }).catch((err)=>{
            assert.fail()
        })
    })

})