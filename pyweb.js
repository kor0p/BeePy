// TODO: deploy to npm
// TODO: make pyweb.min.js

window._DEBUGGER = function _DEBUGGER (error=null) {
    const place_breakpoint_here = 'use variable _locals in console to get locals() from python frame';
}

// utils
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
    document.title = 'PyWeb'
    console.warn(`Document title is not set, use default title: ${document.title}`)
}
if (!window.pyweb || !window.pyweb.config) {
    console.warn(`
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

// could be useful in the future, i.e: get attributes of <script src="pyweb" />
pyweb.script = document.currentScript
const _src = pyweb.script.src

const DEFAULT_CONFIG = {
    // user can specify version of pyodide
    // TODO: check supporting versions of pyodide
    pyodideVersion: '0.23.0',
    // could be useful for some internal checks
    __loading: false,
    // use wrapper, so pyweb.__main__ could be overridden
    onload: () => pyweb.__main__(),
    // extra modules in base dir to load
    modules: [],
}

if (!pyweb.config.path && _src.indexOf('pyweb.js')) {
    pyweb.config.path = _src.substring(0, _src.indexOf('pyweb.js') - 1).replace(/\/+$/, '')
}

const config = mergeDeep(DEFAULT_CONFIG, pyweb.config)
pyweb.__CONFIG__ = config

// loading pyodide script

const indexURL = `https://cdn.jsdelivr.net/pyodide/v${config.pyodideVersion}/full/`
const script = document.createElement('script')
script.type = 'module'
script.src = indexURL + 'pyodide.js'
document.head.appendChild(script)


// defining tools for running python

const rootFolder = '__pyweb_root__'

pyweb.loadFile = async function loadFile (filePath, options = {_internal: false}) {
    if (!options._internal) pyweb.__CURRENT_LOADING_FILE__ = filePath
    return await (await fetch(filePath)).text()
}

pyweb.loadFileSync = function loadFileSync (filePath, options = {_internal: false}) {
    /**
     * Same as pyweb.loadFile, but synchronous
     */
    if (!options._internal) pyweb.__CURRENT_LOADING_FILE__ = filePath
    const req = new XMLHttpRequest()
    req.open("GET", filePath, false)
    req.send(null)
    return req.response
}

pyweb._writeInternalFile = async function _writeInternalFile (file, content) {
    if (!content) content = await pyweb.loadFile(`${config.path}/pyweb/${file}`, {_internal: true})
    pyodide.FS.writeFile(`pyweb/${file}`, content)
}

pyweb._writeInternalFileSync = function _writeInternalFileSync (file) {
    pyodide.FS.writeFile(`pyweb/${file}`, pyweb.loadFileSync(`${config.path}/pyweb/${file}`), {_internal: true})
}

pyweb._writeLocalFile = async function _writeLocalFile (file, content) {
    if (!content) content = await pyweb.loadFile(_lstrip(file), {_internal: true})
    pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
}

pyweb._writeLocalFileSync = function _writeLocalFileSync (file, content) {
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

window.pyf = async function runPythonFile (filePath) {
    return window.py(await pyweb.loadFile(filePath))
}

window.apyf = async function runPythonAsyncFile (filePath) {
    return await window.apy(await pyweb.loadFile(filePath))
}

window.enterPythonModule = async function enterPythonModule (module) {
    try {
        if (module.includes('/')) {
            module = _lstrip(module).replace(/\//g, '.')
        }

        await pyweb._loadLocalModule(module, '__init__.py')
        await apy(`import ${rootFolder}`)
    } catch (e) {
        console.error(e)
        _DEBUGGER(e)
    }
}

if (!pyweb.__main__) {
    pyweb.__main__ = () => {
        console.info('You can override pyweb.__main__ to run code after pyweb finish loading')
    }
}

window.__pyweb_load = async () => {
    await Promise.all([systemLoad(), pywebLoad()])
    window.removeEventListener('load', window.__pyweb_load)
}
window.addEventListener('load', window.__pyweb_load)

async function systemLoad () {
    window.pyodide = await window.loadPyodide({ indexURL })
    pyweb.globals = pyodide.globals
    pyweb.__CONFIG__.__loading = true
    await pyodide.loadPackage('micropip')
    console.log(pyodide._api.sys.version)
}

async function pywebLoad () {
    // load relative modules from pyweb/__init__.py
    const _init = await pyweb.loadFile(`${config.path}/pyweb/__init__.py`, {_internal: true})
    const pywebModules = []
    for (const match of _init.matchAll(/from . import (?<module>.+)/g)) {
        pywebModules.push(`${match.groups.module}.py`)
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

del merge_configs
_globals = _PyWebGlobals(globals())
del _PyWebGlobals
_globals # last evaluated value is returned from 'py' function
`)

    delete pyweb.__CONFIG__.__loading
    // new Proxy(_PyWebGlobals, {
    //     get: (target, symbol) => "get" === symbol ? key => {
    //         let result = target.get(key)
    //         return void 0 === result && (result = builtins_dict.get(key)), result
    //     } : "has" === symbol ? key => target.has(key) || builtins_dict.has(key) : Reflect.get(target, symbol)
    // })

    try {
        await pyweb._loadLocalModule('')
        await apy(`import ${rootFolder}`)
    } catch (e) {
        console.debug(e)
        _DEBUGGER(e)
        console.info('You can add __init__.py near index.html to auto-load your code')
    }

    pyweb.__CURRENT_LOADING_FILE__ = ''
    await config.onload()
}


function mkDirPath(path) {
    const pathParts = path.split('/')

    for (let length = 0; length < pathParts.length; length++) {
        pyodide.FS.mkdir(rootFolder + '/' + pathParts.slice(0, length+1).join('/'))
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


function _getModulesFromLocalInit (initFile, pathDotted) {
    const pywebModules = []
    const localModules = []
    for (const match of initFile.matchAll(/from pyweb.(?<module>.+) import (?<imports>.+)/g)) {
        const file = `${match.groups.module}.py`
        if (config.modules.includes(file)) continue
        pywebModules.push(file)
    }
    for (const match of initFile.matchAll(/from . import (?<module>.+)/g)) {
        localModules.push(`${pathDotted}.${match.groups.module}`)
    }
    config.modules.push(...pywebModules)

    return [pywebModules, localModules]
}


pyweb.__CURRENT_LOADING_FILE__ = ''
pyweb.populateCurrentPath = function populateCurrentPath (path) {
    const currentPath = pyweb.__CURRENT_LOADING_FILE__.replace(/(\/(\w*.py)?)*$/, '')
    return `${currentPath}${currentPath && path ? '/' : ''}${path.replace(/^\/*/, '')}`
}


pyweb._loadLocalModule = async function _loadLocalModule (module, pathToWrite='') {
    let initFile = ''

    const [path, parsedModule, fsPath] = _parseAndMkDirModule(module, true)
    const fullPath = `${path}${path && parsedModule ? '/' : ''}${parsedModule}`
    let initFilePath = fullPath + '.py'

    try {
        initFile = await pyweb.loadFile(_lstrip(initFilePath))
        if (initFile.substring(0, 1) === '<') {
            initFilePath = fullPath + (parsedModule ? `/` : '') + '__init__.py'
            initFile = await pyweb.loadFile(_lstrip(initFilePath))
        }
    } catch (e) {
        console.error(e)
        _DEBUGGER(e)
        return
    }

    if (!pathToWrite) pathToWrite = initFilePath.replace(new RegExp(`^${path}`), fsPath)
    const [pywebModules, localModules] = _getModulesFromLocalInit(initFile, path.replace(/\//g, '.'))

    await Promise.all(pywebModules.map(file => pyweb._writeInternalFile(file)))
    await Promise.all(
        [pyweb._writeLocalFile(pathToWrite, initFile)].concat(
            localModules.map(file => pyweb._loadLocalModule(file))
        )
    )
}


// utils.ensure_sync(js.pyweb._loadLocalModule(module)) doesn't work correctly
pyweb._loadLocalModuleSync = function _loadLocalModuleSync (module, pathToWrite='') {
    let initFile = ''

    const [path, parsedModule, fsPath] = _parseAndMkDirModule(module, true)
    const fullPath = `${path}${path && parsedModule ? '/' : ''}${parsedModule}`
    let initFilePath = fullPath + '.py'

    try {
        initFile = pyweb.loadFileSync(_lstrip(initFilePath))
        if (initFile.substring(0, 1) === '<') {
            initFilePath = fullPath + (parsedModule ? `/` : '') + '__init__.py'
            initFile = pyweb.loadFileSync(_lstrip(initFilePath))
        }
    } catch (e) {
        console.error(e)
        _DEBUGGER(e)
        return
    }

    if (!pathToWrite) pathToWrite = initFilePath.replace(new RegExp(`^${path}`), fsPath)
    const [pywebModules, localModules] = _getModulesFromLocalInit(initFile, path.replace(/\//g, '.'))

    for (const file of pywebModules) {
        pyweb._writeInternalFileSync(file)
    }

    pyweb._writeLocalFileSync(pathToWrite, initFile)
    for (const file of localModules) {
        pyweb._loadLocalModuleSync(file)
    }
}


pyweb._loadLocalFileSync = function _loadLocalFile (filePath) {
    pyweb._writeLocalFileSync(_parseAndMkDirFile(filePath, true).slice(0, 2).join('/'))
}

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
