// TODO: deploy to npm
// TODO: make pyweb.min.js

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

// pyweb config

if (!document.title) {
    // TODO: move to the end, to prevent this warning, if title was set by Head.title = 'Title'
    document.title = 'PyWeb'
    console.warn(`Document title is not set, use default title: ${document.title}`)
}
if (!window.pyweb || !window.pyweb.config) {
    console.log(`
No pyweb config found! Default config will be used
If you have config, you must define it before loading pyweb script
    `)
    if (!window.pyweb) {
        window.pyweb = {}
    }
    if (!pyweb.config) {
        pyweb.config = {}
    }
}

const DEFAULT_CONFIG = {
    // user can specify version of pyodide
    // TODO: check supporting versions of pyodide
    pyodideVersion: '0.23.2',
    // could be useful for some internal checks
    __loading: false,
    // extra modules in base dir to load
    modules: [],
    requirements: [],  // also could be function
}

// could be useful in the future, i.e: get attributes of <script src="pyweb" />
pyweb.script = document.currentScript
const _src = pyweb.script.src
if (!pyweb.config.path && _src.indexOf('pyweb.js')) {
    pyweb.config.path = _src.substring(0, _src.indexOf('pyweb.js') - 1).replace(/\/+$/, '')
}

const config = mergeDeep(DEFAULT_CONFIG, pyweb.config)
pyweb.__CONFIG__ = config
pyweb.addElement = function addElement (mountPoint, elementName, options={}) {
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

// loading pyodide script

const indexURL = `https://cdn.jsdelivr.net/pyodide/v${config.pyodideVersion}/full/`
pyweb.addElement(document.head, 'script', {type: 'module', src: indexURL + 'pyodide.js'})


// defining tools for running python

const rootFolder = '__pyweb_root__'

pyweb.loadFile = async function loadFile (filePath, {_internal=false, checkPathExists=false}={}, _method_head=false) {
    if (!_internal) pyweb.__CURRENT_LOADING_FILE__ = filePath
    if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`
    if (checkPathExists && !(await pyweb.loadFile(filePath, {_internal}, true)).ok) return '<'

    const r = await fetch(filePath, {method: _method_head ? 'HEAD' : 'GET'})
    return _method_head ? r : await r.text()
}

pyweb.loadFileSync = function loadFileSync (filePath, {_internal=false, checkPathExists=false}={}, _method_head=false) {
    if (!_internal) pyweb.__CURRENT_LOADING_FILE__ = filePath
    if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`
    if (checkPathExists && pyweb.loadFileSync(filePath, {_internal}, true).status !== 200) return '<'

    const req = new XMLHttpRequest()
    req.open(_method_head ? 'HEAD' : 'GET', filePath, false)
    req.send(null)
    return _method_head ? req : req.response
}

pyweb._writeInternalFile = async function _writeInternalFile (file, content) {
    if (!content) content = await pyweb.loadFile(`${config.path}/pyweb/${file}`, {_internal: true})
    pyodide.FS.writeFile(`pyweb/${file}`, content)
}

pyweb._writeInternalFileSync = function _writeInternalFileSync (file, content) {
    if (!content) content = pyweb.loadFileSync(`${config.path}/pyweb/${file}`, {_internal: true})
    pyodide.FS.writeFile(`pyweb/${file}`, content)
}

pyweb._writeLocalFile = async function _writeLocalFile (file, content) {
    if (file.substring(0, 6) === 'pyweb/') return await pyweb._writeInternalFile(file.substring(6), content)
    if (!content) content = await pyweb.loadFile(_lstrip(file), {_internal: true})
    pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
}

pyweb._writeLocalFileSync = function _writeLocalFileSync (file, content) {
    if (file.substring(0, 6) === 'pyweb/') return pyweb._writeInternalFileSync(file.substring(6), content)
    if (!content) content = pyweb.loadFileSync(_lstrip(file), {_internal: true})
    pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
}

function _getGlobalsDict (options) {
    if (isObject(options)) {
        return {globals: options.globals || pyweb.globals}
    } else if (options === null) {
        return {globals: pyweb.globals}
    } else {
        console.warn(
            'DeprecationWarning: The globals argument to runPython and runPythonAsync is now passed as a named argument'
        )
        return {globals: options || pyweb.globals}
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

        pyweb._loadLocalModule(module, {pathToWrite: '__init__.py', addCurrentPath: false})
        py(`import ${rootFolder}`)
    } catch (e) {
        console.error(e)
        _DEBUGGER(e)
    }
}

window.__pyweb_load = async () => {
    if (!document.getElementById('pyweb-loading')) {
        const loadingEl = pyweb.addElement(document.body, 'div', {id: 'pyweb-loading', _index: 0})
        pyweb.addElement(loadingEl, 'style', {innerHTML: '#pyweb-loading {display: inline-block; background: none; width: 50px; height: 50px; position: fixed; top: 50%; left: 50%; border: 3px solid rgba(172, 237, 255, 0.5); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; -webkit-animation: spin 1s ease-in-out infinite;} @keyframes spin {to {-webkit-transform: rotate(360deg);}} @-webkit-keyframes spin {to {-webkit-transform: rotate(360deg);}'})
    }

    await Promise.all([systemLoad(), pywebLoad()])
    window.removeEventListener('load', window.__pyweb_load)
}
window.addEventListener('load', window.__pyweb_load)

async function systemLoad () {
    window.pyodide = await window.loadPyodide({ indexURL })
    pyweb.globals = pyodide.globals
    await pyodide.loadPackage('micropip')
    let requirements = pyweb.__CONFIG__.requirements
    if (!Array.isArray(requirements)) requirements = requirements()
    await Promise.all(requirements.map(requirement => pyodide.loadPackage(requirement)))
    pyweb.__CONFIG__.__loading = true
    console.log(pyodide._api.sys.version)
}

async function pywebLoad () {
    // load relative modules from pyweb/__init__.py
    const _init = await pyweb.loadFile(`${config.path}/pyweb/__init__.py`, {_internal: true})
    const pywebModules = []
    for (const match of _init.matchAll(/from pyweb import (?<modules>.+)/g)) {
        for (const module of match.groups.modules.split(/, ?/g)) {
            pywebModules.push(`${module}.py`)
        }
    }
    config.modules.unshift('__init__.py', ...pywebModules)

    // TODO: create wheel and load pyweb modules via pip
    const contents = await Promise.all(
        config.modules.map(file => pyweb.loadFile(`${config.path}/pyweb/${file}`, {_internal: true}))
    )

    while (pyweb.__CONFIG__.__loading === false) {
        await delay(100)
    }
    // pyodide loaded in systemLoad()

    pyodide.FS.mkdir(rootFolder)
    pyodide.FS.mkdir('pyweb')
    await Promise.all(config.modules.map((file, i) => pyweb._writeInternalFile(file, contents[i])))

    pyweb.globals = py(`
import js
from pyweb import __version__
from pyweb.utils import merge_configs, _PyWebGlobals
js.console.log(f'%cPyWeb version: {__version__}', 'color: lightgreen; font-size: 35px')
merge_configs()

del js, merge_configs
_globals = _PyWebGlobals(globals())
del _PyWebGlobals
_globals # last evaluated value is returned from 'py' function
`)

    delete pyweb.__CONFIG__.__loading

    pyweb.__CURRENT_LOADING_FILE__ = ''
    if (pyweb.__main__) {
        await pyweb.__main__()
    } else {
        try {
            pyweb._loadLocalModule('', {checkPathExists: true})
            py(`import ${rootFolder}`)
        } catch (e) {
            console.debug(e)
            console.info('You can add __init__.py near index.html to auto-load your code')
        }
    }
}


function mkDirPath(path, removeFileName=false) {
    const pathParts = path.split('/')
    let maxLength = pathParts.length
    if (removeFileName) maxLength -= 1

    for (let length = 0; length < maxLength; length++) {
        let pathToCreate = pathParts.slice(0, length+1).join('/')
        if (!pathParts.includes('pyweb')) pathToCreate = rootFolder + '/' + pathToCreate
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
        return [pyweb.populateCurrentPath(path), filePath, path]
    }

    return [path, filePath]
}


function _parseAndMkDirModule (module, addCurrentPath) {
    return _parseAndMkDirFile(module, addCurrentPath, '.')
}


pyweb.__CURRENT_LOADING_FILE__ = ''
pyweb.populateCurrentPath = function populateCurrentPath (path) {
    const currentPath = pyweb.__CURRENT_LOADING_FILE__.replace(/(\/(\w*.py)?)*$/, '')
    return `${currentPath}${currentPath && path ? '/' : ''}${path.replace(/^\/*/, '')}`
}
pyweb.getPathWithCurrentPathAndOrigin = function getPathWithCurrentPathAndOrigin (path) {
    path = pyweb.populateCurrentPath(path)
    if (!path.includes('http')) path = `${window.location.origin}/${path}`
    return path
}


pyweb._loadLocalModule = function _loadLocalModule (
    module, {pathToWrite='', addCurrentPath=true, checkPathExists=false}={}
) {
    let moduleFile = ''

    const [path, parsedModule, fsPath] = _parseAndMkDirModule(module, addCurrentPath)
    const fullPath = `${path}${path && parsedModule ? '/' : ''}${parsedModule}`
    let moduleFilePath = fullPath + '.py'

    try {
        moduleFile = moduleFilePath === '.py' ? '<' : pyweb.loadFileSync(_lstrip(moduleFilePath), {checkPathExists})
        if (isHTML(moduleFile)) {
            moduleFilePath = fullPath + (parsedModule ? `/` : '') + '__init__.py'
            moduleFile = pyweb.loadFileSync(_lstrip(moduleFilePath), {checkPathExists})
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

    pyweb._writeLocalFileSync(pathToWrite, moduleFile)

    return false
}

pyweb.listenerCheckFunctions = {
    'prevent': 'preventDefault',
    'stop': 'stopPropagation',
    'stop_all': 'stopImmediatePropagation',
}

pyweb.addAsyncListener = function addAsyncListener (el, eventName, method, modifiers, options={}) {
    async function _listener (event) {
        for (const modifier of modifiers) {
            event[pyweb.listenerCheckFunctions[modifier]]()
        }

        try {
            return await method(event)
        } catch (err) {
            _DEBUGGER(err)
        }
    }
    el.addEventListener(eventName, _listener, options)
    return _listener
}