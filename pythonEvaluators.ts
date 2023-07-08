import { ExecArgs, PythonEvaluator, PythonResult } from ".";

export class PythonExecutors {
    executors: PythonEvaluator[]
    currentExecutorIndex: number

    start(){
        let i: number = 0
        for(i=0;i++;i<3){
            const pyExecutor = new PythonEvaluator()
            pyExecutor.start(()=>{})
            pyExecutor.evaluatorName = i.toString()
            pyExecutor.onResult = result => {
                // Other executor may send a result right before it dies
                // So we use this functin to only capture result from active executor
                if(i == this.currentExecutorIndex) this.onResult(result)
            }
            this.executors.push(pyExecutor)
        }
    }

    /**
     * Sends code to the current executor
     * If current executor is busy, nothing happens
     */
    execCodeCurrent(code: ExecArgs){
        this.executors[this.currentExecutorIndex].execCode(code)
    }

    /**
     * sends code to a free executor to be executed
     * Side-effect: restarts dirty executors
     */
    execCode(){
        // to check for free executor:
        // freeEvaluator = evaluators.first(evaluator=>evaluator.free)

        // cancel setinterval
        // restart all Executing or DirtyFree processes
        // if no freshfree executor:
        setInterval(()=>{
            // if free executor, send code
        }, 60)
        // else: send code to first free executor
        // send code func:
        //   foo.execCode(data)
        //   set last ran executor
    }

    /**
	 * Overwrite this with your own handler.
	 * is called when active executor fails or completes
	 */
	onResult(foo: PythonResult) { }

	/**
	 * Overwrite this with your own handler.
	 * Is called when active executor prints
	 * @param {string} foo
	 */
	onPrint(foo: string) { }

	/**
	 * Overwrite this with your own handler. 
	 * Is called when active executor logs stderr
	 * @param {string} foo
	 */
	onStderr(foo: string) { }
}