/*global suite, test*/ //comment for eslint

// This test uses TDD Mocha. see https://mochajs.org/ for help
// http://ricostacruz.com/cheatsheets/mocha-tdd

// The module 'assert' provides assertion methods from node
const assert = require("assert")

const evals = require("./index")

suite("PythonEvaluator Tests", () => {
    let pyEvaluator = new evals.PythonEvaluator()
    let input = {evalCode:"", savedCode: ""}

    test("sanity check: 1+1=2", () => {
        assert.equal(1+1,2)
    })

    test("PythonEvaluator returns result", function(done){
        pyEvaluator.onResult = (result)=>{
            console.log(result)
            assert.notEqual(result, null)
            done()
        }
        input.evalCode = "x"
        pyEvaluator.execCode(input)
    })

    test("PythonEvaluator returns error when bad code", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.notEqual(result.ERROR, null)
            assert.notEqual(result.ERROR.trim(), "")
            done()
        }
        input.evalCode = "x="
        pyEvaluator.execCode(input)
    })

    test("PythonEvaluator returns user variables", function(done){
        pyEvaluator.onResult = (result)=>{ 
            assert.equal(result.userVariables['x'], 1)
            done()
        }
        input.evalCode = "x=1"
        pyEvaluator.execCode(input)
    })

    test("PythonEvaluator can print stdout", function(done){
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
        pyEvaluator.execCode()
    })

    test("PythonEvaluator can print multiple lines", function(done){
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

    test("PythonEvaluator returns result after print", function(done){
        pyEvaluator.onPrint = (stdout)=>{ 
            assert.equal(stdout, "hello world")
            assert.equal(pyEvaluator.running, true)
        }

        pyEvaluator.onResult = () => {
            assert.equal(pyEvaluator.running, false)
            done()
        }

        input.evalCode = "print('hello world')"
        pyEvaluator.execCode(input)
    })

})