# AREPL-backend [![Build Status](https://travis-ci.org/Almenon/AREPL-backend.svg?branch=master)](https://travis-ci.org/Almenon/AREPL-backend) [![Build status](https://ci.appveyor.com/api/projects/status/24o0d29l7ci9bif3?svg=true)](https://ci.appveyor.com/project/Almenon/arepl-backend) [![npm version](https://badge.fury.io/js/arepl-backend.svg)](https://badge.fury.io/js/arepl-backend)

JS interface to python evaluator for AREPL. 

Evaluates python code and sends back the user variables and/or any errors.

Although it is meant for AREPL, it is not dependent upon AREPL and can be used by any project.

**Important Note**: this should ONLY be used to execute trusted code.  It does not have any security features whatsoever.

## Installation

> npm install [arepl-backend](https://www.npmjs.com/package/arepl-backend)

must have python 3 

## Usage

see <https://github.com/Almenon/AREPL-vscode> for example useage. 

## For developers:

Semantic release cheatsheet:

    | Commit message       | Release type |
    |----------------------|--------------|
    | fix: msg             | patch        |
    | feat: msg            | feature      |
    | perf: msg            |              |
    | BREAKING CHANGE: msg | breaking     |

## API

<!-- Generated by documentation.js. Update this documentation by updating the source code. -->

#### Table of Contents

-   [constructor](#constructor)
    -   [Parameters](#parameters)
-   [executing](#executing)
-   [running](#running)
-   [debounce](#debounce)
-   [execCode](#execcode)
    -   [Parameters](#parameters-1)
-   [sendStdin](#sendstdin)
    -   [Parameters](#parameters-2)
-   [restart](#restart)
    -   [Parameters](#parameters-3)
-   [stop](#stop)
-   [start](#start)
-   [onResult](#onresult)
    -   [Parameters](#parameters-4)
-   [onPrint](#onprint)
    -   [Parameters](#parameters-5)
-   [onStderr](#onstderr)
    -   [Parameters](#parameters-6)
-   [handleResult](#handleresult)
    -   [Parameters](#parameters-7)
-   [checkSyntax](#checksyntax)
    -   [Parameters](#parameters-8)
-   [checkSyntaxFile](#checksyntaxfile)
    -   [Parameters](#parameters-9)
-   [formatPythonException](#formatpythonexception)
    -   [Parameters](#parameters-10)
    -   [Examples](#examples)

### constructor

starts python_evaluator.py

#### Parameters

-   `options`  Process / Python options. If not specified sensible defaults are inferred. (optional, default `{}`)

### executing

whether python is busy executing inputted code

### running

whether python backend process is running / not running

### debounce

delays execution of function by ms milliseconds, resetting clock every time it is called
Useful for real-time execution so execCode doesn't get called too often
thanks to <https://stackoverflow.com/a/1909508/6629672>

### execCode

does not do anything if program is currently executing code

#### Parameters

-   `code`  

### sendStdin

#### Parameters

-   `message` **[string](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String)** 

### restart

kills python process and restarts.  Force-kills if necessary after 50ms.
After process restarts the callback passed in is invoked

#### Parameters

-   `callback`   (optional, default `()=>{}`)

### stop

kills python process.  force-kills if necessary after 50ms.
you can check python_evaluator.running to see if process is dead yet

### start

starts python_evaluator.py. Will NOT WORK with python 2

### onResult

Overwrite this with your own handler.
is called when program fails or completes

#### Parameters

-   `foo`  

### onPrint

Overwrite this with your own handler.
Is called when program prints

#### Parameters

-   `foo` **[string](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String)** 

### onStderr

Overwrite this with your own handler.
Is called when program logs stderr

#### Parameters

-   `foo` **[string](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String)** 

### handleResult

handles pyshell results and calls onResult / onPrint

#### Parameters

-   `results` **[string](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String)** 

### checkSyntax

checks syntax without executing code

#### Parameters

-   `code` **[string](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String)** 

Returns **[Promise](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Promise)** rejects w/ stderr if syntax failure

### checkSyntaxFile

checks syntax without executing code

#### Parameters

-   `filePath` **[string](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String)** 

Returns **[Promise](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Promise)** rejects w/ stderr if syntax failure

### formatPythonException

gets rid of unnecessary File "<string>" message in exception

#### Parameters

-   `err`  

#### Examples

```javascript
err:
Traceback (most recent call last):\n  File "<string>", line 1, in <module>\nNameError: name \'x\' is not defined\n
```
