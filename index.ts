import {PythonShell} from 'python-shell'

export interface PythonResult{
	userError:string,
	userVariables:object,
	execTime:number,
	totalPyTime:number,
	totalTime:number,
	internalError:string,
	caller: string,
	lineno:number,
	done: boolean
}

export class PythonEvaluator{
    
    private static readonly identifier = "6q3co7"

    /**
     * whether python is busy executing inputted code
     */
    evaling = false

    /**
     * whether python backend is on/off
     */
    running = false

    restarting = false
    private pythonOptions: string[]
    private pythonPath:string
    private startTime:number
    private pythonEvalFolderPath = __dirname + '/python/'

    /**
     * an instance of python-shell. See https://github.com/extrabacon/python-shell
     */
    pyshell:PythonShell

	/**
	 * starts pythonEvaluator.py 
	 * @param {string} pythonPath the path to run python. By default evaluator uses 'python' if on windows or else 'python3'.
	 * @param {[string]} pythonOptions see https://docs.python.org/3/using/cmdline.html#miscellaneous-options.
	 */
	constructor(pythonPath:string = null, pythonOptions: string[] = ['-u']){

		this.evaling = false // whether python is busy executing inputted code
		this.running = false // whether python backend is on/off
		this.restarting = false
		this.pythonOptions = pythonOptions

		if(process.platform == "darwin"){
			//needed for Mac to prevent ENOENT
			process.env.PATH = ["/usr/local/bin", process.env.PATH].join(":")
		}

		if(pythonPath == null){
			// for non-windows OS it is best to use python3 instead of python
			// Mac and Ubuntu both have python being v2 by default
			// archlinux and freebsd both use v3 as default, but also provide python3 command
			this.pythonPath = process.platform != "win32" ? "python3" : "python"
		}
		else this.pythonPath = pythonPath
	}

	
	/**
	 * does not do anything if program is currently evaling code
	 */
	execCode(code:{evalCode:string,savedCode:string,filePath:string}){
		if(this.evaling) return
		this.evaling = true
		this.startTime = Date.now()
		this.pyshell.send(JSON.stringify(code))
	}

	/**
	 * @param {string} message 
	 */
	sendStdin(message:string){
		this.pyshell.send(message)
	}

	/**
	 * kills python process and restarts.  Force-kills if necessary after 50ms.
	 * After process restarts the callback passed in is invoked
	 */
	restart(callback=()=>{}){

		this.restarting = false

		// register callback for restart
		// using childProcess callback instead of pyshell callback
		// (pyshell callback only happens when process exits voluntarily)
		this.pyshell.childProcess.on('exit',()=>{
			this.restarting = true
			this.evaling = false
			this.startPython()
			callback()
		})

		this.stop()
	}

	/**
	 * kills python process.  force-kills if necessary after 50ms.
	 * you can check PythonEvaluator.running to see if process is dead yet
	 */
	stop(){
		// pyshell has 50 ms to die gracefully
		this.running = !this.pyshell.childProcess.kill()
		if(this.running) console.info("pyshell refused to die")
		else this.evaling = false

		setTimeout(()=>{
			if(this.running && !this.restarting){
				// murder the process with extreme prejudice
				this.running = !this.pyshell.childProcess.kill('SIGKILL')
				if(this.running){
					console.error("the python process simply cannot be killed!")
				}
				else this.evaling = false
			}
		}, 50)
	}

	/**
	 * starts pythonEvaluator.py. Will NOT WORK with python 2
	 */
	startPython(){
		console.log("Starting Python...")
		this.pyshell = new PythonShell('pythonEvaluator.py', {
			scriptPath: this.pythonEvalFolderPath,
			pythonOptions: this.pythonOptions,
			pythonPath: this.pythonPath,
		})
		this.pyshell.on('message', message => {
			this.handleResult(message)
		})
		this.pyshell.on('stderr', (log)=>{
			this.onStderr(log)
		})
		this.running = true
	}

	/**
	 * Overwrite this with your own handler.
	 * is called when program fails or completes
	 */
	onResult(foo: PythonResult){}

	/**
	 * Overwrite this with your own handler.
	 * Is called when program prints
	 * @param {string} foo
	 */
	onPrint(foo: string){}

	/**
	 * Overwrite this with your own handler.
	 * Is called when program logs stderr
	 * @param {string} foo
	 */
	onStderr(foo: string){}

	/**
	 * handles pyshell results and calls onResult / onPrint
	 * @param {string} results 
	 */
	handleResult(results:string) {
		let pyResult:PythonResult = {
			userError:"",
			userVariables: {},
            execTime:0,
            totalTime:0,
			totalPyTime:0,
			internalError:"",
			caller:"",
			lineno:-1,
			done:true
		}

        //result should have identifier, otherwise it is just a printout from users code
        if(results.startsWith(PythonEvaluator.identifier)){
            results = results.replace(PythonEvaluator.identifier,"")
			pyResult = JSON.parse(results)
			this.evaling = !pyResult['done']

			if(pyResult['internalError'] != null && pyResult['internalError'].startsWith('json error with stdin: ')){
				console.warn("error in python evaluator converting stdin to JSON. " +
				"User probably just sent stdin without input() in his program.\n" + pyResult['internalError'])
				return
			}
			
			pyResult.execTime = pyResult.execTime*1000 // convert into ms
			pyResult.totalPyTime = pyResult.totalPyTime*1000
			
			//@ts-ignore pyResult.userVariables is sent to as string, we convert to object
			pyResult.userVariables = JSON.parse(pyResult.userVariables)

            if(pyResult.userError != ""){
                pyResult.userError = this.formatPythonException(pyResult.userError)
			}

			pyResult.totalTime = Date.now()-this.startTime
			this.onResult(pyResult)
		}
        else{
            this.onPrint(results)
		}
	}

	/**
	 * checks syntax without executing code
	 * @param {string} code
	 * @returns {Promise} rejects w/ stderr if syntax failure
	 */
	async checkSyntax(code:string){
		return PythonShell.checkSyntax(code);
	}

	/**
	 * checks syntax without executing code
	 * @param {string} filePath
	 * @returns {Promise} rejects w/ stderr if syntax failure
	 */
	async checkSyntaxFile(filePath:string){
		// note that this should really be done in pythonEvaluator.py
		// but communication with that happens through just one channel (stdin/stdout)
		// so for now i prefer to keep this seperate

		return PythonShell.checkSyntaxFile(filePath);
	}

	/**
	 * gets rid of unnecessary exception data, among other things
	 * @param {string} err
	 * @example err:
	 * "Traceback (most recent call last):
	 *   File "pythonEvaluator.py", line 26, in <module>
	 * 	exec(data['evalCode'], evalLocals)
	 *   line 4, in <module>
	 * NameError: name 'y' is not defined"
	 * @returns {string}
	 */
	formatPythonException(err:string){

		//replace File "<string>" (pointless)
		err = err.replace(/File \"<string>\", /g, "")

		// we need to further modify bottom traceback
		let index = err.lastIndexOf("Traceback (most recent call last):")
		let bottomTraceback = err.slice(index)
		let otherTracebacks = err.slice(0,index)
	
		let errLines = bottomTraceback.split('\n')
	
		// error caught in pythonEvaluator so it includes that stack frame
		// user should not see it, so remove first and second lines:
		errLines = [errLines[0]].concat(errLines.slice(3))		
		bottomTraceback = errLines.join('\n')

		return otherTracebacks + bottomTraceback
	}

	/**
	 * delays execution of function by ms millaseconds, resetting clock every time it is called
	 * Useful for real-time execution so execCode doesn't get called too often
	 * thanks to https://stackoverflow.com/a/1909508/6629672
	 */
	debounce = (function(){
		let timer:any = 0;
		return function(callback, ms: number, ...args: any[]){
			clearTimeout(timer);
			timer = setTimeout(callback, ms, args);
		};
	})();
}
