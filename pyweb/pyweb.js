import { mergeDeep, delay } from './utils.js'
import './debugger.js'

window.delay = delay
function get_py_tag(i) {
    return () => window[`$${i}`]._py
}
Object.defineProperties(
    window,
    Object.fromEntries(new Array(10).fill(null).map(
        (_, i) => [`py${i}`, {get: get_py_tag(i)}]
    ))
)
/**
 * usage:
 * > py0
 * evaluates $0._py
 * available for py0-py9
 */

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

const indexURL = 'https://cdn.jsdelivr.net/pyodide/v0.19.1/full/'
const script = document.createElement('script')
script.type = 'module'
script.src = indexURL + 'pyodide.js'
document.head.appendChild(script)

async function _load () {
    window.pyodide = await window.loadPyodide({ indexURL })

    window.PYWEB = {}
    PYWEB.loadRawFile = async function loadRawFile (filePath) {
        return await (await fetch(filePath)).text()
    }
    PYWEB.handleTextForImport = function handleTextForImport (text) {
        return text.replace(
            /# ?\[PYWEB IGNORE START\]([\w\W]*)# ?\[PYWEB IGNORE END\]/gm,
            function (string, group, index) {
                const countOfLines = (group.match(/\n/g) || []).length
                return new Array(countOfLines).fill('\n').join('')
            },
        )
    }
    PYWEB.loadFile = async function loadFile (filePath) {
        window.__CURRENT_LOADING_FILE__ = filePath
        return PYWEB.handleTextForImport(await PYWEB.loadRawFile(filePath))
    }
    window.py = function runPython (...args) {
        try {
            return pyodide.runPython(...args)
        } catch (e) {
            console.debug(e)
            window._DEBUGGER(e)
            throw e
        }
    }
    window.apy = async function runPythonAsync (code, ...args) {
        await pyodide.loadPackagesFromImports(code)
        try {
            return await pyodide.runPythonAsync(code, ...args)
        } catch (e) {
            console.debug(e)
            window._DEBUGGER(e)
            throw e
        }
    }
    window.pyf = async function runPythonFile (filePath) {
        return window.py(await PYWEB.loadFile(filePath))
    }
    window.apyf = async function runPythonAsyncFile (filePath) {
        return await window.apy(await PYWEB.loadFile(filePath))
    }
}

if (!pyweb.__main__) {
    pyweb.__main__ = () => {
        console.warn('You can override pyweb.__main__ to run code after pyweb finish loading')
    }
}
const DEFAULT_CONFIG = {
    debug: false,
    path: '..',
    // use wrapper, so pyweb.__main__ could be overridden
    onload: () => pyweb.__main__(),
    // extra modules in base dir to load
    modules: ['local_storage.py', 'utils.py', 'framework.py', 'tags.py', 'style.py'],
}

// could be useful in the future, i.e: get attributes of <script src="pyweb" />
pyweb.script = document.currentScript

const config = mergeDeep(DEFAULT_CONFIG, pyweb.config)
pyweb.__CONFIG__ = config

window.addEventListener('load', async function () {
    await _load()
    await pyodide.loadPackage('micropip')
    py('import sys; print(sys.version)')

    // TODO: create wheel and load via pip
    for (const file of config.modules) {
        await apyf(`${config.path}/pyweb/${file}`)
    }

    await config.onload()
})

Node.prototype.insertChild = function (child, index) {
    /**
     *
     * # Python version
     * # TODO: check why it's not working
     * @js_func()
     * def _node_insert_child(self: js.Element, child, index=None):
     *     if index is None or index >= len(self.children):
     *         try:
     *             self.appendChild(child)
     *         except Exception as e:
     *             _debugger(e)
     *     else:
     *         self.insertBefore(child, self.children[index])
     *
     * js.Node.prototype.insertChild = _node_insert_child
     */
    if (index == null || index >= this.children.length) {
        this.appendChild(child)
    } else {
        this.insertBefore(child, this.children[index])
    }
}