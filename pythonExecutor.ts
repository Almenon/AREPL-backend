import { PythonShell, Options, NewlineTransformer } from 'python-shell'
import { EOL } from 'os'
import { randomBytes } from 'crypto'

export interface FrameSummary {
	_line: string
	filename: string
	lineno: number
	locals: {}
	name: string
}

export interface UserError {
	__cause__: UserError
	__context__: UserError
	_str: string
	cause: UserError
	context: UserError
	exc_traceback: {}
	exc_type: {
		"py/type": string
	}
	stack: {
		"py/seq": FrameSummary[]
	}
	/* following for syntax errors only */
	filename?: string
	lineno?: string
	msg?: string
	offset?: number
	text?: string
}

export interface ExecArgs {
	evalCode: string,
	filePath: string,
	usePreviousVariables?: boolean,
	show_global_vars?: boolean,
	default_filter_vars: string[],
	default_filter_types: string[]
}

export interface PythonResult {
	userError: UserError,
	userErrorMsg?: string,
	userVariables: object,
	execTime: number,
	totalPyTime: number,
	totalTime: number,
	internalError: string,
	caller: string,
	lineno: number,
	done: boolean,
	startResult: boolean,
	evaluatorName: string,
}

/**
 * Starting = Starting or restarting. 
 * Ending = Process is exiting. 
 * Executing = Executing inputted code. 
 * DirtyFree = evaluator may have been polluted by side-effects from previous code, but is free for more code. 
 * FreshFree = evaluator is ready for the first run of code
 */
export enum PythonState {
	Starting,
	Ending,
	Executing,
	DirtyFree,
	FreshFree
}

export class PythonExecutor {
	private static readonly areplPythonBackendFolderPath = __dirname + '/python/'

	// how long between SIGTERM and SIGKILL, in ms
	static GRACE_PERIOD = 50

	state: PythonState = PythonState.Starting
	finishedStartingCallback: Function
	evaluatorName: string
	private startTime: number

	/**
	 * an instance of python-shell. See https://github.com/extrabacon/python-shell
	 */
	pyshell: PythonShell

	/**
	 * starts python_evaluator.py 
	 * @param options Process / Python options. If not specified sensible defaults are inferred. 
	 */
	constructor(private options: Options = {}) {

		if (!options.env) options.env = {}
		if (process.platform == "darwin") {
			// needed for Mac to prevent ENOENT
			options.env.PATH = ["/usr/local/bin", process.env.PATH].join(":")
		}
		else if (process.platform == "win32") {
			// needed for windows for encoding to match what it would be in terminal
			// https://docs.python.org/3/library/sys.html#sys.stdin
			options.env.PYTHONIOENCODING = "utf8"
		}

		// python-shell buffers untill newline is reached in text mode
		// so we use binary instead to skip python-shell buffering
		// this lets user flush without newline
		this.options.mode = 'binary'
		this.options.stdio = ['pipe', 'pipe', 'pipe', 'pipe']
		if (!options.pythonPath) this.options.pythonPath = PythonShell.defaultPythonPath
		if (!options.scriptPath) this.options.scriptPath = PythonExecutor.areplPythonBackendFolderPath

		this.evaluatorName = randomBytes(16).toString('hex')
	}


	/**
	 * does not do anything if program is currently executing code 
	 */
	execCode(code: ExecArgs) {
		if (this.state == PythonState.Executing){
			console.error('Incoming code detected while process is still executing. \
			This should never happen')
		}
		this.state = PythonState.Executing
		this.startTime = Date.now()
		this.pyshell.send(JSON.stringify(code) + EOL)
	}

	/**
	 * @param {string} message
	 */
	sendStdin(message: string) {
		this.pyshell.send(message)
	}

	/**
	 * kills python process and restarts.  Force-kills if necessary after 50ms. 
	 * After process restarts the callback passed in is invoked
	 */
	restart(callback = () => { }) {

		this.state = PythonState.Ending

		// register callback for restart
		// using childProcess callback instead of pyshell callback
		// (pyshell callback only happens when process exits voluntarily)
		this.pyshell.childProcess.on('exit', () => {
			this.start(callback)
		})

		this.stop()
	}

	/**
	 * Kills python process.  Force-kills if necessary after 50ms.
	 * You can check python_evaluator.running to see if process is dead yet
	 */
	stop(kill_immediately=false) {
		this.state = PythonState.Ending
		const kill_signal = kill_immediately ? 'SIGKILL' : 'SIGTERM'
		this.pyshell.childProcess.kill(kill_signal)
		
		if(!kill_immediately){
			// pyshell has 50 ms to die gracefully
			setTimeout(() => {
				if (this.state == PythonState.Ending) {
					// python didn't respect the SIGTERM, force-kill it
					this.pyshell.childProcess.kill('SIGKILL')
				}
			}, PythonExecutor.GRACE_PERIOD)
		}
	}

	/**
	 * starts python_evaluator.py.
	 */
	start(finishedStartingCallback) {
		this.state = PythonState.Starting
		console.log("Starting Python...")
		this.finishedStartingCallback = finishedStartingCallback
		this.startTime = Date.now()
		this.pyshell = new PythonShell('arepl_python_evaluator.py', this.options)

		const resultPipe = this.pyshell.childProcess.stdio[3]
		const newlineTransformer = new NewlineTransformer()
		resultPipe.pipe(newlineTransformer).on('data', this.handleResult.bind(this))

		this.pyshell.stdout.on('data', (message: Buffer) => {
			this.onPrint(message.toString())
		})
		this.pyshell.stderr.on('data', (log: Buffer) => {
			this.onStderr(log.toString())
		})
	}

	/**
	 * Overwrite this with your own handler.
	 * is called when program fails or completes
	 */
	onResult(foo: PythonResult) { }

	/**
	 * Overwrite this with your own handler.
	 * Is called when program prints
	 * @param {string} foo
	 */
	onPrint(foo: string) { }

	/**
	 * Overwrite this with your own handler. 
	 * Is called when program logs stderr
	 * @param {string} foo
	 */
	onStderr(foo: string) { }

	/**
	 * handles pyshell results and calls onResult / onPrint
	 * @param {string} results 
	 */
	handleResult(results: string) {
		let pyResult: PythonResult = {
			userError: null,
			userErrorMsg: "",
			userVariables: {},
			execTime: 0,
			totalTime: 0,
			totalPyTime: 0,
			internalError: "",
			caller: "",
			lineno: -1,
			done: true,
			startResult: false,
			evaluatorName: this.evaluatorName
		}

		try {
			pyResult = JSON.parse(results)
			if(pyResult.startResult){
				console.log(`Finished starting in ${Date.now() - this.startTime}`)
				this.state = PythonState.FreshFree
				this.finishedStartingCallback()
				return
			}
			if(pyResult['done'] == true){
				this.state = PythonState.DirtyFree
			}

			pyResult.execTime = pyResult.execTime * 1000 // convert into ms
			pyResult.totalPyTime = pyResult.totalPyTime * 1000

			//@ts-ignore pyResult.userVariables is sent to as string, we convert to object
			pyResult.userVariables = JSON.parse(pyResult.userVariables)
			//@ts-ignore pyResult.userError is sent to as string, we convert to object
			pyResult.userError = pyResult.userError ? JSON.parse(pyResult.userError) : {}

			if (pyResult.userErrorMsg) {
				pyResult.userErrorMsg = this.formatPythonException(pyResult.userErrorMsg)
			}
			pyResult.totalTime = Date.now() - this.startTime
			this.onResult(pyResult)

		} catch (err) {
			if (err instanceof Error) {
				err.message = err.message + "\nresults: " + results
			}
			throw err
		}
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
	 * gets rid of unnecessary File "<string>" message in exception
	 * @example err:
	 * Traceback (most recent call last):\n  File "<string>", line 1, in <module>\nNameError: name \'x\' is not defined\n
	 */
	private formatPythonException(err: string) {
		//replace File "<string>" (pointless)
		err = err.replace(/File \"<string>\", /g, "")
		return err
	}
}
