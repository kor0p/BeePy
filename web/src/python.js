import {_debugger, isObject} from './utils'


function _getGlobalsDict (options) {
    let globals
    if (isObject(options)) {
        globals = options.globals || beepy.globals
    } else if (options === null) {
        globals = beepy.globals
    } else {
        throw Error('ArgumentError: The argument "globals" is passed as a named argument')
    }
    return {globals, locals: globals}
}


class Python {
    run (code, options=null) {
        try {
            return pyodide.runPython(code, _getGlobalsDict(options))
        } catch (e) {
            console.debug(e)
            _debugger(e)
            throw e
        }
    }

    async runAsync (code, options=null) {
        if (options && !options.skipImports) {
            await pyodide.loadPackagesFromImports(code)
        }
        try {
            return await pyodide.runPythonSyncifying(code, _getGlobalsDict(options))
        } catch (e) {
            console.debug(e)
            _debugger(e)
            throw e
        }
    }
}

export const python = new Python()
window.py = python.run
window.apy = python.runAsync
