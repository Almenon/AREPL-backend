/*global suite, test*/ //comment for eslint

// This test uses TDD Mocha. see https://mochajs.org/ for help
// http://ricostacruz.com/cheatsheets/mocha-tdd

// The module 'assert' provides assertion methods from node
import * as assert from 'assert'

import { PythonExecutors } from './pythonExecutors'

suite("PythonExecutors", () => {
    let pyExecutors = new PythonExecutors()
    let input = {
        evalCode: "",
        filePath: "",
        usePreviousVariables: false,
        show_global_vars: true,
        default_filter_vars: [],
        default_filter_types: ["<class 'module'>", "<class 'function'>"]
    }
    const pythonStartupTime = 3000
    const num_executors = 2

    suiteSetup(function () {
        this.timeout(pythonStartupTime + 500)
    })

    setup(function (done) {
        pyExecutors.onPrint = () => { }
        pyExecutors.onStderr = () => { }
        pyExecutors.onResult = () => { }
        pyExecutors.start(num_executors)
        done()
    })

    teardown(function(){
        pyExecutors.stop(true)
    })

    test("can do multiple executions", function (done) {
        // we do three test runs because given that only two executors exist:
        // if first fails: something is wrong with first executor
        // if second fails: something is wrong with second executor
        // if thid fails: logic that waits for a executor to become free is broken
        let num_results = 0
        pyExecutors.onResult = (result) => {
            num_results+=1
            if(num_results == 1){
                assert.strictEqual(result.userVariables['x'], 1)
                input.evalCode = "x=2"
                pyExecutors.execCode(input)
            }
            else if(num_results == 2){
                assert.strictEqual(result.userVariables['x'], 2)
                input.evalCode = "x=3"
                pyExecutors.execCode(input)
            }
            else if(num_results > num_executors){
                assert.strictEqual(result.userVariables['x'], 3)
                done()
            }
        }
        input.evalCode = "x=1"
        pyExecutors.execCode(input)
    })

    test("last execution takes precedence", function (done) {
        pyExecutors.onResult = (result) => {
            assert.strictEqual(result.userVariables['x'], 2)
            done()
        }
        input.evalCode = "x=1"
        pyExecutors.execCode(input)
        input.evalCode = "x=2"
        pyExecutors.execCode(input)
    })

})
