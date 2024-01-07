import {_debugger, isObject} from './utils'

class Python {
    _getGlobalsDict (options) {
        if (isObject(options)) {
            return {globals: options.globals || beepy.globals}
        } else if (options === null) {
            return {globals: beepy.globals}
        } else {
            console.warn('DeprecationWarning: The argument "globals" is now passed as a named argument')
            return {globals: options || beepy.globals}
        }
    }

    run (code, options=null) {
        try {
            return pyodide.runPython(code, this._getGlobalsDict(options))
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
            return await pyodide.runPythonAsync(code, this._getGlobalsDict(options))
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
