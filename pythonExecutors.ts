import { Options, PythonShell } from "python-shell";
import { ExecArgs, PythonExecutor, PythonResult, PythonState } from "./pythonExecutor";

export * from './pythonExecutor'

/**
 * Starts multiple python executors for running user code. 
 * Will manage them for you, so you can treat this class
 * as a single executor.
 */
export class PythonExecutors {
    private executors: PythonExecutor[] = []
    private currentExecutorIndex: number = 0
    private waitForFreeExecutor: NodeJS.Timeout
    private wait_for_other_runs_to_complete: NodeJS.Timeout

    constructor(public options: Options = {}){}

    start(numExecutors=3){
        // we default to three executors, as it should be enough so that there is always
        // one available to accept incoming code

        if(this.executors.length != 0) throw Error('already started!')

        for(let i = 0; i < numExecutors; i++){
            console.log('starting executor ' + i.toString())
            const pyExecutor = new PythonExecutor(this.options)
            pyExecutor.start(()=>{})
            pyExecutor.evaluatorName = i.toString()
            pyExecutor.onResult = result => {
                // Other executor may send a result right before it dies
                // So we use this function to only capture result from active executor
                if(i == this.currentExecutorIndex) this.onResult(result)
            }
            pyExecutor.onPrint = print => {
                if(i == this.currentExecutorIndex) this.onPrint(print)
            }
            pyExecutor.onStderr = stderr => {
                if(i == this.currentExecutorIndex) this.onStderr(stderr)
            }
            pyExecutor.pyshell.on('error', this.onError)
            pyExecutor.pyshell.childProcess.on('exit', exitCode => {
                if(exitCode != 0) this.onAbnormalExit(exitCode)
            })
            this.executors.push(pyExecutor)
        }
    }

    /**
     * Sends code to the current executor. 
     * If current executor is busy, nothing happens
     */
    execCodeCurrent(code: ExecArgs){
        this.executors[this.currentExecutorIndex].execCode(code)
    }

    /**
     * sends code to a free executor to be executed
     * Side-effect: restarts dirty executors
     */
    execCode(code: ExecArgs){
        // old code is now irrelevant, if we are still waiting to send old code
        // we should stop waiting
        clearInterval(this.waitForFreeExecutor)
        // this timeout should definitely not still be going on, but we clear it just in case
        clearTimeout(this.wait_for_other_runs_to_complete)

        let last_run_still_executing = false
        if(this.executors.some(executor => executor.state == PythonState.Executing)){
            last_run_still_executing = true
        }
        // executors running old code are now irrelevant, restart them
        this.executors.filter(executor => executor.state == PythonState.Executing || executor.state == PythonState.DirtyFree)
            .forEach(executor => executor.restart())

        if(last_run_still_executing){
            // wait for last run to complete
            // we don't want to run two programs at once
            // which could cause a race condition
            this.wait_for_other_runs_to_complete = setTimeout(this.exec_when_free_executor.bind(this, code), PythonExecutor.GRACE_PERIOD+5)
        } else{
            this.exec_when_free_executor(code)
        }
    }

    private exec_when_free_executor(code: ExecArgs){
        let freeExecutor = this.executors.find(executor=>executor.state == PythonState.FreshFree)
        if(!freeExecutor){
            this.waitForFreeExecutor = setInterval(()=>{
                freeExecutor = this.executors.find(executor=>executor.state == PythonState.FreshFree)
                if(freeExecutor){
                    freeExecutor.execCode(code)
                    this.currentExecutorIndex = parseInt(freeExecutor.evaluatorName)
                    clearInterval(this.waitForFreeExecutor)
                }
            }, 60)
        }
        else{
            freeExecutor.execCode(code)
            this.currentExecutorIndex = parseInt(freeExecutor.evaluatorName)
        }
    }

    stop(kill_immediately=false){
        clearInterval(this.waitForFreeExecutor)
        this.executors.forEach(executor => executor.stop(kill_immediately))
        this.executors = []
    }

	/**
	 * checks syntax without executing code
	 * @param {string} code
	 * @returns {Promise} rejects w/ stderr if syntax failure
	 */
	async checkSyntax(code: string) {
		return PythonShell.checkSyntax(code);
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

	/**
	 * Overwrite this with your own handler. 
	 * Is called when there is a Node.JS error event with the python process
     *  The 'error' event is emitted whenever:
            The process could not be spawned, or
            The process could not be killed, or
            Sending a message to the child process failed.
	 */
	onError(err: NodeJS.ErrnoException) { }

    onAbnormalExit(exitCode: number) {}

	/**
	 * delays execution of function by ms milliseconds, resetting clock every time it is called
	 * Useful for real-time execution so execCode doesn't get called too often
	 * thanks to https://stackoverflow.com/a/1909508/6629672
	 */
	debounce = (function () {
		let timer: any = 0;
		return function (callback, ms: number, ...args: any[]) {
			clearTimeout(timer);
			timer = setTimeout(callback, ms, args);
		};
	})();
}