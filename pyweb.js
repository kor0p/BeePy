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


// console tools

function getPyTag(i) {
    return () => window[`$${i}`]._py
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
 * evaluates $0._py
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
    if (!window.pyweb.config) {
        window.pyweb.config = {}
    }
}

// could be useful in the future, i.e: get attributes of <script src="pyweb" />
pyweb.script = document.currentScript

const DEFAULT_CONFIG = {
    pyodide_version: '0.21.0a3',
    // use wrapper, so pyweb.__main__ could be overridden
    onload: () => pyweb.__main__(),
    // extra modules in base dir to load
    modules: [],
}

if (!pyweb.config.path && pyweb.script.src.indexOf('pyweb.js')) {
    pyweb.config.path = pyweb.script.src.substring(0, pyweb.script.src.indexOf('pyweb.js') - 1).replace(/\/+$/, '')
}

const config = mergeDeep(DEFAULT_CONFIG, pyweb.config)
pyweb.__CONFIG__ = config

// loading pyodide

const indexURL = `https://cdn.jsdelivr.net/pyodide/v${config.pyodide_version}/full/`
const script = document.createElement('script')
script.type = 'module'
script.src = indexURL + 'pyodide.js'
document.head.appendChild(script)


// defining tools for running python

const root_folder = '__pyweb_root__'

pyweb.loadFile = async function loadFile (filePath) {
    pyweb.__CURRENT_LOADING_FILE__ = filePath
    return await (await fetch(filePath)).text()
}

pyweb.loadFileSync = function loadFileSync (filePath) {
    /**
     * Same as pyweb.loadFile, but synchronous
     * NOTE: Method is available only after Pyodide was fully loaded
     *       Use pyweb.__main__ callback as start point to be sure
     */
    pyweb.__CURRENT_LOADING_FILE__ = filePath
    return pyodide.pyodide_py.http.open_url(filePath).read()
}

pyweb._writeInternalFile = async function _writeInternalFile (file) {
    pyodide.FS.writeFile(`pyweb/${file}`, await pyweb.loadFile(`${config.path}/pyweb/${file}`))
}

pyweb._writeInternalFileSync = function _writeInternalFileSync (file) {
    pyodide.FS.writeFile(`pyweb/${file}`, pyweb.loadFileSync(`${config.path}/pyweb/${file}`))
}

pyweb._writeLocalFile = async function _writeLocalFile (file, content) {
    if (!content) content = await pyweb.loadFile(`./${_lstrip(file)}`)
    pyodide.FS.writeFile(`${root_folder}/${file}`, content)
}

pyweb._writeLocalFileSync = function _writeLocalFileSync (file, content) {
    if (!content) content = pyweb.loadFileSync(`./${_lstrip(file)}`)
    pyodide.FS.writeFile(`${root_folder}/${file}`, content)
}

window.py = function runPython (code, options={}) {
    try {
        return pyodide.runPython(code, options.globals)
    } catch (e) {
        console.debug(e)
        window._DEBUGGER(e)
        throw e
    }
}

window.apy = async function runPythonAsync (code, options={}) {
    if (!options.skipImports) {
        await pyodide.loadPackagesFromImports(code)
    }
    try {
        return await pyodide.runPythonAsync(code, options.globals)
    } catch (e) {
        console.debug(e)
        window._DEBUGGER(e)
        throw e
    }
}

window.pyf = async function runPythonFile (filePath) {
    return window.py(await pyweb.loadFile(filePath))
}

window.apyf = async function runPythonAsyncFile (filePath) {
    return await window.apy(await pyweb.loadFile(filePath))
}

if (!pyweb.__main__) {
    pyweb.__main__ = () => {
        console.info('You can override pyweb.__main__ to run code after pyweb finish loading')
    }
}

window.addEventListener('load', async function () {
    window.pyodide = await window.loadPyodide({ indexURL })
    await Promise.all([systemLoad(), pywebLoad()])
})


async function systemLoad () {
    await pyodide.loadPackage('micropip')
    py(`
import sys
print(sys.version)
del sys
`)
}

async function pywebLoad () {
    // load relative modules from pyweb/__init__.py
    pyodide.FS.mkdir(root_folder)
    pyodide.FS.mkdir('pyweb')
    const _init = await pyweb.loadFile(`${config.path}/pyweb/__init__.py`)
    const pyweb_modules = []
    for (const match of _init.matchAll(/from . import (?<module>.+)/g)) {
        pyweb_modules.push(`${match.groups.module}.py`)
    }
    config.modules.unshift('__init__.py', ...pyweb_modules)

    // TODO: create wheel and load pyweb modules via pip
    await Promise.all(config.modules.map(file => pyweb._writeInternalFile(file)))

    py(`
import js
from pyweb import __version__, utils
js.console.log(f'%cPyWeb version: {__version__}', 'color: black; font-size: 35px')
utils.merge_configs()
del js, utils
`)

    try {
        await pyweb._loadLocalFile('')
        await apy(`import ${root_folder}`)
    } catch (e) {
        console.debug(e)
        console.info('You can add __init__.py near index.html to auto-load your code')
    }

    await config.onload()
}


function _parseAndMkDirModule (module) {
    let path = '',
        path_dotted = ''

    if (module && module.indexOf('.') !== -1) {
        let path_parts = module.split('.').reverse()
        module = path_parts.shift()
        path_parts = path_parts.reverse()
        for (let length = 0; length < path_parts.length; length++) {
            pyodide.FS.mkdir(root_folder + '/' + path_parts.slice(0, length+1).join('/'))
        }
        path = path_parts.join('/')
        path_dotted = path.replace(/\//g, '.')
    }

    return [path, path_dotted, module, module ? `/${module}/` : '/']
}


function _getModulesFromLocalInit (init_file, path_dotted) {
    const pyweb_modules = []
    const local_modules = []
    for (const match of init_file.matchAll(/from pyweb.(?<module>.+) import (?<imports>.+)/g)) {
        const file = `${match.groups.module}.py`
        if (config.modules.includes(file)) continue
        pyweb_modules.push(file)
    }
    for (const match of init_file.matchAll(/from . import (?<module>.+)/g)) {
        local_modules.push(`${path_dotted}.${match.groups.module}`)
    }
    config.modules.push(...pyweb_modules)

    return [pyweb_modules, local_modules]
}


pyweb._loadLocalFile = async function _loadLocalFile (module) {
    let init_file = ''

    const [path, path_dotted, _module, module_path] = _parseAndMkDirModule(module)
    module = _module
    let init_file_path = `${path}${module_path}__init__.py`

    try {
        init_file = await pyweb.loadFile(`./${_lstrip(init_file_path)}`)
        if (init_file.substring(0, 1) === '<') {
            init_file_path = `${path}/${module}.py`
            init_file = await pyweb.loadFile(`./${_lstrip(init_file_path)}`)
        }
    } catch (e) {
        console.error(e)
        window._DEBUGGER(e)
        return
    }

    const [pyweb_modules, local_modules] = _getModulesFromLocalInit(init_file, path_dotted)

    await Promise.all(pyweb_modules.map(file => pyweb._writeInternalFile(file)))
    await Promise.all(
        [pyweb._writeLocalFile(init_file_path, init_file)].concat(
            local_modules.map(file => pyweb._loadLocalFile(file))
        )
    )
}


// TODO: try utils.ensure_sync(js.pyweb._loadLocalFile(module))
pyweb._loadLocalFileSync = function _loadLocalFileSync (module) {
    let init_file = ''

    const [path, path_dotted, _module, module_path] = _parseAndMkDirModule(module)
    module = _module
    let init_file_path = `${path}${module_path}__init__.py`

    try {
        init_file = pyweb.loadFileSync(`./${_lstrip(init_file_path)}`)
        if (init_file.substring(0, 1) === '<') {
            init_file_path = `${path}/${module}.py`
            init_file = pyweb.loadFileSync(`./${_lstrip(init_file_path)}`)
        }
    } catch (e) {
        console.error(e)
        window._DEBUGGER(e)
        return
    }

    const [pyweb_modules, local_modules] = _getModulesFromLocalInit(init_file, path_dotted)

    for (const file of pyweb_modules) {
        pyweb._writeInternalFileSync(file)
    }

    pyweb._writeLocalFileSync(init_file_path, init_file)
    for (const file of local_modules) {
        pyweb._loadLocalFileSync(file)
    }
}

Node.prototype.insertChild = function (child, index) {
    if (index == null || index >= this.children.length) {
        this.appendChild(child)
    } else {
        this.insertBefore(child, this.children[index])
    }
}

Node.prototype.safeRemoveChild = function (child) {
    if (this.contains(child)) {
        return this.removeChild(child)
    }
}
