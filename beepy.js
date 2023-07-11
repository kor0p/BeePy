// TODO: deploy to npm
// TODO: make beepy.min.js

window._DEBUGGER = function _DEBUGGER (error=null) {
    const place_breakpoint_here = 'use variable _locals in console to get locals() from python frame';
}

// utils
Node.prototype.insertChild = function (child, index) {
    if (index == null || index >= this.children.length) {
        if (typeof child === 'string') {
            this.insertAdjacentHTML('beforeend', child)
        } else {
            this.appendChild(child)
        }
    } else {
        if (typeof child === 'string') {
            this.children[index].insertAdjacentHTML('beforebegin', child)
        } else {
            this.insertBefore(child, this.children[index])
        }
    }
}

Node.prototype.safeRemoveChild = function (child) {
    if (this.contains(child)) {
        return this.removeChild(child)
    }
}

function isObject (obj) {
  return obj && typeof obj === 'object'
}

function mergeDeep(...objects) {
  return objects.reduce((acc, obj) => {
    Object.entries(obj).forEach(([key, objValue]) => {
      const accValue = acc[key]

      if (Array.isArray(accValue) && Array.isArray(objValue)) {
        acc[key] = accValue.concat(...objValue)
      } else if (isObject(accValue) && isObject(objValue)) {
        acc[key] = mergeDeep(accValue, objValue)
      } else {
        acc[key] = objValue
      }
    })

    return acc
  }, {})
}

async function delay(ms) {
  return new Promise(r => setTimeout(r, ms))
}

window.delay = delay


function _lstrip (text) {
    return text.replace(/^\/+/, '')
}

function isHTML (text) {
    return text.replace(/^\s+/, '').substring(0, 1) === '<'
}

const _PY_TAG_ATTRIBUTE = '__PYTHON_TAG__'


// console tools

function getPyTag(i) {
    return () => window[`$${i}`][_PY_TAG_ATTRIBUTE]
}

Object.defineProperties(
    window,
    Object.fromEntries(new Array(10).fill(null).map(
        (_, i) => [`py${i}`, {get: getPyTag(i)}]
    ))
)
/**
 * usage:
 * > py0
 * evaluates $0.__PYTHON_TAG__
 * available for py0-py9
 */

// beepy config

if (!window.beepy || !window.beepy.config) {
    console.log(`
No beepy config found! Default config will be used
If you have config, you must define it before loading beepy script
    `)
    if (!window.beepy) {
        window.beepy = {}
    }
    if (!beepy.config) {
        beepy.config = {}
    }
}

const DEFAULT_CONFIG = {
    // user can specify version of pyodide
    // TODO: check supporting versions of pyodide
    pyodideVersion: '0.23.4',
    requirements: [],  // also could be function
}

// useful for getting attributes of <script src="beepy" />
beepy.script = document.currentScript
const _src = beepy.script.src
if (!beepy.config.path && _src.indexOf('beepy.js') !== -1) {
    beepy.config.path = _src.substring(0, _src.indexOf('beepy.js') - 1).replace(/\/+$/, '')
}

const config = mergeDeep(DEFAULT_CONFIG, beepy.config)
beepy.__CONFIG__ = config
beepy.addElement = function addElement (mountPoint, elementName, options={}) {
    const element = document.createElement(elementName, {is: options._is})
    const index = options._index
    delete options._is
    delete options._index

    for (const [optionName, optionValue] of Object.entries(options)) {
        element[optionName] = optionValue
    }
    mountPoint.insertChild(element, index)
    return element
}
beepy.addElement(
    document.head, 'link', {rel: 'stylesheet', type: 'text/css', href: `${beepy.config.path}/beepy.css`}
)

// loading pyodide script

const indexURL = `https://cdn.jsdelivr.net/pyodide/v${config.pyodideVersion}/full/`
beepy.addElement(document.head, 'script', {type: 'module', src: indexURL + 'pyodide.js'})


// defining tools for running python

const rootFolder = '__beepy_root__'

beepy.loadFile = async function loadFile (filePath, {checkPathExists=false}={}, _method_head=false) {
    beepy.__CURRENT_LOADING_FILE__ = filePath
    if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`
    if (checkPathExists && !(await beepy.loadFile(filePath, {}, true)).ok) return '<'

    const r = await fetch(filePath, {method: _method_head ? 'HEAD' : 'GET'})
    return _method_head ? r : await r.text()
}

beepy.loadFileSync = function loadFileSync (filePath, {checkPathExists=false}={}, _method_head=false) {
    beepy.__CURRENT_LOADING_FILE__ = filePath
    if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`
    if (checkPathExists && beepy.loadFileSync(filePath, {}, true).status !== 200) return '<'

    const req = new XMLHttpRequest()
    req.open(_method_head ? 'HEAD' : 'GET', filePath, false)
    req.send(null)
    return _method_head ? req : req.response
}

beepy._writeLocalFile = async function _writeLocalFile (file, content) {
    if (!content) content = await beepy.loadFile(_lstrip(file))
    pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
}

beepy._writeLocalFileSync = function _writeLocalFileSync (file, content) {
    if (!content) content = beepy.loadFileSync(_lstrip(file))
    pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
}

function _getGlobalsDict (options) {
    if (isObject(options)) {
        return {globals: options.globals || beepy.globals}
    } else if (options === null) {
        return {globals: beepy.globals}
    } else {
        console.warn(
            'DeprecationWarning: The globals argument to runPython and runPythonAsync is now passed as a named argument'
        )
        return {globals: options || beepy.globals}
    }
}

window.py = function runPython (code, options=null) {
    try {
        return pyodide.runPython(code, _getGlobalsDict(options))
    } catch (e) {
        console.debug(e)
        _DEBUGGER(e)
        throw e
    }
}

window.apy = async function runPythonAsync (code, options=null) {
    if (options && !options.skipImports) {
        await pyodide.loadPackagesFromImports(code)
    }
    try {
        return await pyodide.runPythonAsync(code, _getGlobalsDict(options))
    } catch (e) {
        console.debug(e)
        _DEBUGGER(e)
        throw e
    }
}

window.enterPythonModule = async function enterPythonModule (module) {
    try {
        if (module.includes('/')) {
            module = _lstrip(module).replace(/\//g, '.')
        }

        beepy._loadLocalModule(module, {pathToWrite: '__init__.py', addCurrentPath: false})
        py(`import ${rootFolder}`)
    } catch (e) {
        console.error(e)
        _DEBUGGER(e)
    }
}

beepy.startLoading = function startLoading ({ mountPoint=null, text='Loading...' }={}) {
    if (!!document.getElementById('beepy-loading')) return
    beepy.addElement(
        mountPoint || document.body, 'div', {id: 'beepy-loading', _index: 0, innerHTML: `<span>${text}</span>`}
    )
}
beepy.stopLoading = function stopLoading () {
    const loadingEl = document.getElementById('beepy-loading')
    if (!!loadingEl) loadingEl.remove()
}

window.__beepy_load = async () => {
    beepy.startLoading()

    window.pyodide = await window.loadPyodide({ indexURL })

    pyodide.FS.mkdir(rootFolder)

    beepy.globals = pyodide.globals
    await pyodide.loadPackage('micropip')
    beepy.pip = pyodide.pyimport('micropip')
    console.log(pyodide._api.sys.version)

    let requirements = beepy.__CONFIG__.requirements
    if (!Array.isArray(requirements)) requirements = requirements()

    await Promise.all([...requirements.map(beepy.pip.install), _loadDevServer(), _loadBeePyModule()])

    window.removeEventListener('load', window.__beepy_load)
}
window.addEventListener('load', window.__beepy_load)

beepy.DEV__hot_reload = false
async function _loadDevServer () {
    try {  // TODO: add flag parameter for this
        beepy.DEV__hot_reload_ws = new WebSocket('ws://localhost:8998/')
    } catch (e) {}  // Dev Hot Reload server is not started
    beepy.DEV__hot_reload = !!beepy.DEV__hot_reload_ws
    if (!beepy.DEV__hot_reload) return

    await apy('import importlib as _dev_importlib; import sys as _dev_sys')
    beepy.DEV__hot_reload_ws.onmessage = async ({ data: file }) => {
        const data = beepy._filePathToModuleAndRealFileCache[file]
        if (data) {
            const [fileToWrite, module] = data
            if (module) {
                await beepy._writeLocalFile(fileToWrite, await beepy.loadFile(file))
                await apy(`_dev_importlib.reload(_dev_sys.modules['${module}'])`)
            }
        }
        await apy(`_dev_importlib.reload(_dev_sys.modules['${rootFolder}'])`)
        await _main({reload: true})
    }
}

async function _loadBeePyModule () {
    let version
    if (_src.indexOf('beepy.js') === -1) {
        throw new Error('Invalid BeePy source! Cannot get version of framework')
    } else {
        version = (new URL(_src)).searchParams.get('v')
        if (version) {
            if (version === 'latest') {
                version = ''
            }
        } else {
            console.warn('No version specified in BeePy source! The latest will be used')
            version = ''
        }
    }
    try {
        await beepy.pip.install(`beepy_web${(version ? '==' : '') + version}`)
    } catch {
        await beepy.pip.install(`${beepy.config.path}/dist/beepy_web-${version}-py3-none-any.whl`)
    }

    beepy.globals = py(`
import js
from beepy import __version__
from beepy.utils.internal import merge_configs, _BeePyGlobals
js.console.log(f'%cBeePy version: {__version__}', 'color: lightgreen; font-size: 35px')
merge_configs()

del js, merge_configs
_globals = _BeePyGlobals(globals())
del _BeePyGlobals
_globals # last evaluated value is returned from 'py' function
`)
    await _main()
}

async function _main (options={reload: false}) {
    beepy.__CURRENT_LOADING_FILE__ = ''
    if (beepy.__main__) {
        await beepy.__main__()
    } else {
        try {
            beepy._loadLocalModule('', {checkPathExists: true})
            py(`import ${rootFolder}`)
        } catch (e) {
            console.debug(e)
            if (options.reload) return
            console.info('You can add __init__.py near index.html to auto-load your code')
        }
    }
}


function mkDirPath(path, removeFileName=false) {
    const pathParts = path.split('/')
    let maxLength = pathParts.length
    if (removeFileName) maxLength -= 1

    for (let length = 1; length <= maxLength; length++) {
        let pathToCreate = rootFolder + '/' + pathParts.slice(0, length).join('/')
        if (!pyodide.FS.analyzePath(pathToCreate).exists) pyodide.FS.mkdir(pathToCreate)
    }
}


function _parseAndMkDirFile (filePath, addCurrentPath = false, separator='/') {
    let path = ''

    if (filePath && filePath.indexOf(separator) !== -1) {
        let pathParts = filePath.split(separator).reverse()
        filePath = pathParts.shift()
        path = pathParts.reverse().join('/')
        mkDirPath(path)
    }

    if (addCurrentPath) {
        return [beepy.populateCurrentPath(path), filePath, path]
    }

    return [path, filePath]
}


function _parseAndMkDirModule (module, addCurrentPath) {
    return _parseAndMkDirFile(module, addCurrentPath, '.')
}


beepy.__CURRENT_LOADING_FILE__ = ''
beepy._filePathToModuleAndRealFileCache = {}
beepy.populateCurrentPath = function populateCurrentPath (path) {
    const currentPath = beepy.__CURRENT_LOADING_FILE__.replace(/(\/(\w*.py)?)*$/, '')
    return `${currentPath}${currentPath && path ? '/' : ''}${path.replace(/^\/*/, '')}`
}
beepy.getPathWithCurrentPathAndOrigin = function getPathWithCurrentPathAndOrigin (path) {
    path = beepy.populateCurrentPath(path)
    if (!path.includes('http')) path = `${window.location.origin}/${path}`
    return path
}


beepy._loadLocalModule = function _loadLocalModule (
    module, {pathToWrite='', addCurrentPath=true, checkPathExists=false}={}
) {
    let moduleFile = ''

    const [path, parsedModule, fsPath] = _parseAndMkDirModule(module, addCurrentPath)
    const fullPath = `${path}${path && parsedModule ? '/' : ''}${parsedModule}`
    let moduleFilePath = fullPath + '.py'

    try {
        moduleFile = moduleFilePath === '.py' ? '<' : beepy.loadFileSync(_lstrip(moduleFilePath), {checkPathExists})
        if (isHTML(moduleFile)) {
            moduleFilePath = fullPath + (parsedModule ? `/` : '') + '__init__.py'
            moduleFile = beepy.loadFileSync(_lstrip(moduleFilePath), {checkPathExists})
            if (isHTML(moduleFile)) {
                return 'Python file not found'
            }
        }
    } catch (e) {
        console.error(e)
        return e
    }

    if (!pathToWrite) pathToWrite = moduleFilePath.replace(new RegExp(`^${path}`), fsPath)
    if (pathToWrite.includes('/')) mkDirPath(pathToWrite, true)

    beepy._filePathToModuleAndRealFileCache[moduleFilePath] = [pathToWrite, module]
    beepy._writeLocalFileSync(pathToWrite, moduleFile)

    return false
}

beepy.listenerCheckFunctions = {
    'prevent': 'preventDefault',
    'stop': 'stopPropagation',
    'stop_all': 'stopImmediatePropagation',
}

function _handleAsyncListener (method, modifiers) {
    return async function (event) {
        for (const modifier of modifiers) {
            event[beepy.listenerCheckFunctions[modifier]]()
        }

        try {
            return await method(event)
        } catch (err) {
            _DEBUGGER(err)
        }
    }
}
beepy.addAsyncListener = function addAsyncListener (el, eventName, method, modifiers, options={}) {
    _listener = _handleAsyncListener(method, modifiers)  // should freeze parameters
    el.addEventListener(eventName, _listener, options)
    return _listener
}
