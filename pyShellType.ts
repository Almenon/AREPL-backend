import { EventEmitter } from "events";
import { ChildProcess } from "child_process";

/**
 * Mock python-shell class just for typing
 */
export class pythonShellTyping extends EventEmitter{
    childProcess: ChildProcess

    /**
     * An interactive Python shell exchanging data through stdio
     * @param {string} script    The python script to execute
     * @param {object} [options] The launch options (also passed to child_process.spawn)
     * @constructor
     */
    constructor(script:string, options:object) {super()};

    // allow global overrides for options
    defaultOptions = {};

    // built-in formatters
    format = {
        text: function toText(data:string):string {return ""},
        json: function toJson(data:object):string {return ""}
    };

    // built-in parsers
    parse = {
        text: function asText(data) {},
        json: function asJson(data:string):object {return {}}
    };

    /**
     * Runs a Python script and returns collected messages
     * @param  {string}   script   The script to execute
     * @param  {Object}   options  The execution options
     * @param  {Function} callback The callback function to invoke with the script results
     * @return {PythonShell}       The PythonShell instance
     */
    run(script:string, options:Object, callback:Function) {};

    /**
     * Parses an error thrown from the Python process through stderr
     * @param  {string|Buffer} data The stderr contents to parse
     * @return {Error} The parsed error with extended stack trace when traceback is available
     */
    parseError (data:string|Buffer) {};

    /**
     * Sends a message to the Python shell through stdin
     * Override this method to format data to be sent to the Python process
     * @param {string|Object} data The message to send
     * @returns {PythonShell} The same instance for chaining calls
     */
    send (message:string|Object) {};

    /**
     * Parses data received from the Python shell stdout stream and emits "message" events
     * This method is not used in binary mode
     * Override this method to parse incoming data from the Python process into messages
     * @param {string|Buffer} data The data to parse into messages
     */
    receive (data:string|Buffer) {};

    /**
     * Closes the stdin stream, which should cause the process to finish its work and close
     * @returns {PythonShell} The same instance for chaining calls
     */
    end(callback) {};
}