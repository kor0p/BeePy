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
    pyodideVersion: '0.23.3',
    // could be useful for some internal checks
    __loading: false,
    // extra modules in base dir to load
    modules: [],
    requirements: [],  // also could be function
}

// could be useful in the future, i.e: get attributes of <script src="beepy" />
beepy.script = document.currentScript
const _src = beepy.script.src
if (!beepy.config.path && _src.indexOf('beepy.js')) {
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

beepy.loadFile = async function loadFile (filePath, {_internal=false, checkPathExists=false}={}, _method_head=false) {
    if (!_internal) beepy.__CURRENT_LOADING_FILE__ = filePath
    if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`
    if (checkPathExists && !(await beepy.loadFile(filePath, {_internal}, true)).ok) return '<'

    const r = await fetch(filePath, {method: _method_head ? 'HEAD' : 'GET'})
    return _method_head ? r : await r.text()
}

beepy.loadFileSync = function loadFileSync (filePath, {_internal=false, checkPathExists=false}={}, _method_head=false) {
    if (!_internal) beepy.__CURRENT_LOADING_FILE__ = filePath
    if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`
    if (checkPathExists && beepy.loadFileSync(filePath, {_internal}, true).status !== 200) return '<'

    const req = new XMLHttpRequest()
    req.open(_method_head ? 'HEAD' : 'GET', filePath, false)
    req.send(null)
    return _method_head ? req : req.response
}

beepy._writeInternalFile = async function _writeInternalFile (file, content) {
    if (!content) content = await beepy.loadFile(`${config.path}/beepy/${file}`, {_internal: true})
    pyodide.FS.writeFile(`beepy/${file}`, content)
}

beepy._writeInternalFileSync = function _writeInternalFileSync (file, content) {
    if (!content) content = beepy.loadFileSync(`${config.path}/beepy/${file}`, {_internal: true})
    pyodide.FS.writeFile(`beepy/${file}`, content)
}

beepy._writeLocalFile = async function _writeLocalFile (file, content) {
    if (file.substring(0, 6) === 'beepy/') return await beepy._writeInternalFile(file.substring(6), content)
    if (!content) content = await beepy.loadFile(_lstrip(file), {_internal: true})
    pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
}

beepy._writeLocalFileSync = function _writeLocalFileSync (file, content) {
    if (file.substring(0, 6) === 'beepy/') return beepy._writeInternalFileSync(file.substring(6), content)
    if (!content) content = beepy.loadFileSync(_lstrip(file), {_internal: true})
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
    await Promise.all([systemLoad(), beepyLoad()])
    window.removeEventListener('load', window.__beepy_load)
}
window.addEventListener('load', window.__beepy_load)

async function systemLoad () {
    window.pyodide = await window.loadPyodide({ indexURL })
    beepy.globals = pyodide.globals
    await pyodide.loadPackage('micropip')
    let requirements = beepy.__CONFIG__.requirements
    if (!Array.isArray(requirements)) requirements = requirements()
    await Promise.all(requirements.map(requirement => pyodide.loadPackage(requirement)))
    beepy.__CONFIG__.__loading = true
    console.log(pyodide._api.sys.version)
}

async function beepyLoad () {
    // load relative modules from beepy/__init__.py
    const _init = await beepy.loadFile(`${config.path}/beepy/init.py`, {_internal: true})
    const beepyModules = []
    for (const match of _init.matchAll(/from beepy import (?<modules>.+)/g)) {
        for (const module of match.groups.modules.split(/, ?/g)) {
            beepyModules.push(`${module}.py`)
        }
    }
    config.modules.unshift('__init__.py', ...beepyModules)

    // TODO: create wheel and load beepy modules via pip
    const contents = await Promise.all(
        config.modules.map(file => beepy.loadFile(`${config.path}/beepy/${file === '__init__.py' ? 'init.py' : file}`, {_internal: true}))
    )

    while (beepy.__CONFIG__.__loading === false) {
        await delay(100)
    }
    // pyodide loaded in systemLoad()

    pyodide.FS.mkdir(rootFolder)
    pyodide.FS.mkdir('beepy')
    await Promise.all(config.modules.map((file, i) => beepy._writeInternalFile(file, contents[i])))

    beepy.globals = py(`
import js
from beepy import __version__
from beepy.utils import merge_configs, _BeePyGlobals
js.console.log(f'%cBeePy version: {__version__}', 'color: lightgreen; font-size: 35px')
merge_configs()

del js, merge_configs
_globals = _BeePyGlobals(globals())
del _BeePyGlobals
_globals # last evaluated value is returned from 'py' function
`)

    delete beepy.__CONFIG__.__loading

    beepy.__CURRENT_LOADING_FILE__ = ''
    if (beepy.__main__) {
        await beepy.__main__()
    } else {
        try {
            beepy._loadLocalModule('', {checkPathExists: true})
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
        if (!pathParts.includes('beepy')) pathToCreate = rootFolder + '/' + pathToCreate
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

    beepy._writeLocalFileSync(pathToWrite, moduleFile)

    return false
}

beepy.listenerCheckFunctions = {
    'prevent': 'preventDefault',
    'stop': 'stopPropagation',
    'stop_all': 'stopImmediatePropagation',
}

beepy.addAsyncListener = function addAsyncListener (el, eventName, method, modifiers, options={}) {
    async function _listener (event) {
        for (const modifier of modifiers) {
            event[beepy.listenerCheckFunctions[modifier]]()
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