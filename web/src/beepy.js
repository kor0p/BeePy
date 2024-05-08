import {_debugger, _lstrip, addHTMLElement, get_meta, isObjectEmpty, mergeDeep} from './utils'
import {AsyncFiles, Files, rootFolder, SyncFiles, SyncFiles as StaticFiles} from './files'
import {dev_server} from './dev-server'
import {python} from './python'

const _script = document.currentScript
let localConfig = {}
if (!!window.beepy) {
    localConfig = window.beepy
}

class BeePy {
    __version__ = '0.10.1'

    pyodideIndexURL = null
    globals = null
    dev_server = dev_server
    dev_path = ''
    python_api = python

    static _default_config = {
        include: ['.env'],
        pyodideVersion: '0.25.1',
        random_seed: get_meta('beepy::config:random_seed') || 0,
        server_side: get_meta('beepy::config:server_side') || '',
        requirements: [],  // also could be function
    }

    // aliases for PythonAPI
    addElement = addHTMLElement
    files = Files

    constructor (localConfig) {
        if (isObjectEmpty(localConfig)) {
            console.log(`
No beepy config found! Default config will be used
If you have config, you must define it before loading beepy script
            `)
        }

        this.config = mergeDeep(BeePy._default_config, localConfig.config || {})

        if (!window.navigator.webdriver) {
            this._updateConfig()
        }

        // Here never will be 'server' (this is set a little later). But it's fine
        if (this.config.server_side !== 'client') {
            this._loadPyodideScript()
        }
    }

    _updateConfig () {
        if (this.config.server_side === 'server') {
            this.config._ssr_all_routes = []
        }

        const path = _script.src.substring(0, _script.src.indexOf('beepy.js') - 1).replace(/\/+$/, '')
        this.dev_path = path.split('/').slice(0, -2).join('/')
    }

    startLoading ({ mountPoint=document.body, text='Loading...' }={}) {
        if (!!document.getElementById('beepy-loading')) return
        this.addElement(mountPoint, 'div', {id: 'beepy-loading', _index: 0, innerHTML: `<span>${text}</span>`})
    }

    stopLoading () {
        const loadingEl = document.getElementById('beepy-loading')
        if (!!loadingEl) loadingEl.remove()
    }

    // Listeners

    listenerCheckFunctions = {
        'prevent': 'preventDefault',
        'stop': 'stopPropagation',
        'stop_all': 'stopImmediatePropagation',
    }

    _handleAsyncListener (method, modifiers) {
        return async (event) => {
            for (const modifier of modifiers) {
                event[this.listenerCheckFunctions[modifier]]()
            }

            try {
                return await method(event)
            } catch (err) {
                _debugger(err)
            }
        }
    }

    addAsyncListener (el, eventName, method, modifiers, options={}) {
        const _listener = this._handleAsyncListener(method, modifiers)  // should freeze parameters
        el.addEventListener(eventName, _listener, options)
        return _listener
    }

    // Modules
    loadModule (module, {pathToWrite='', addCurrentPath=true}={}) {
        let moduleFile

        if (module.includes('/')) {
            const href = window.location.href.substring(window.location.origin.length)
            if (module.substring(0, 2) === '..') {
                module = `${href.split('/').slice(0, -2).join('/')}${module.substring(2)}`
            } else if (module[0] === '.') {
                module = `${href.split('/').slice(0, -1).join('/')}${module.substring(1)}`
            }
            module = _lstrip(module).replace(/\//g, '.')
        }

        const [path, parsedModule, fsPath = ''] = Files._parseAndMkDirModule(module, addCurrentPath)
        const fullPath = `${path}${path && parsedModule ? '/' : ''}${parsedModule}`
        let moduleFilePath = `${fullPath}${parsedModule ? '/' : ''}__init__.py`

        try {
            moduleFile = StaticFiles.loadFile(moduleFilePath)
        } catch (e) {
            moduleFilePath = `${fullPath}.py`
            moduleFile = StaticFiles.loadFile(moduleFilePath)
        }

        if (pathToWrite === '_raw_') {
            pathToWrite = moduleFilePath
        } else if (!pathToWrite) {
            pathToWrite = moduleFilePath.replace(new RegExp(`^${path}`), fsPath)
        }
        if (pathToWrite.includes('/')) Files.mkDirPath(pathToWrite, true)

        this.dev_server._filePathToModuleAndRealFileCache[moduleFilePath] = [pathToWrite, module]
        SyncFiles._writeFile(pathToWrite, moduleFile)
        return fullPath
    }

    async enterModule (module) {
        Files._enteringModule = module
        try {
            const fullModulePath = beepy.loadModule(module, {pathToWrite: '_raw_', addCurrentPath: false})
            beepy.python_api.run(`import ${fullModulePath.replace(/\//g, '.')}`)
        } catch (e) {
            console.error(e)
            _debugger(e)
        }
        Files._enteringModule = null
    }

    async enterRootModule (module) {
        try {
            beepy.loadModule(module, {pathToWrite: '__init__.py', addCurrentPath: false})
            beepy.python_api.run(`import ${rootFolder}`)
        } catch (e) {
            console.error(e)
            _debugger(e)
        }
    }

    __main__ = false  // set beepy.__main__ to call custom function on setUp

    async _main (options={reload: false}) {
        Files._lastLoadedFile = ''
        if (!!this.__main__) {
            return await this.__main__()
        }

        let attrModule = _script.getAttribute('bee-module')
        if (attrModule) {
            await this.enterRootModule(attrModule)
            return
        }

        try {
            this.loadModule('')
            this.python_api.run(`import ${rootFolder}`)
        } catch (e) {
            console.debug(e)
            if (options.reload) return
            console.info('You can add __init__.py near index.html to auto-load your code')
        }
    }

    // Load
    _loadPyodideScript () {
        // loading pyodide script
        // TODO: find way to import it from npm. I tried official package, but it's built for NodeJS, not for the web
        this.pyodideIndexURL = `https://cdn.jsdelivr.net/pyodide/v${this.config.pyodideVersion}/full/`
        addHTMLElement(document.head, 'script', {type: 'module', src: this.pyodideIndexURL + 'pyodide.js'})
    }

    async _load_env () {
        let envFileExists = true
        for (const file of this.config.include) {
            try {
                await AsyncFiles._writeFile(Files._parseAndMkDirFile(file).join('/'))
            } catch (e) {
                if (file === '.env') {
                    envFileExists = false
                    continue
                }
                console.warn(`File ${file} was not found on the server`)
            }
        }

        if (!envFileExists) {
            try {
                await AsyncFiles._writeFile('.env', await AsyncFiles.loadFile(`${this.dev_path}/.env`))
            } catch (e) {}
        }
    }

    async _load () {
        window.removeEventListener('load', this._load)
        if (window.navigator.webdriver) {
            this._updateConfig()
        }

        if (this.config.server_side !== 'client') {
            this.startLoading()
        }

        window.pyodide = await window.loadPyodide({ indexURL: this.pyodideIndexURL })

        pyodide.FS.mkdir(rootFolder)

        this.globals = pyodide.globals
        await pyodide.loadPackage('micropip')
        this.pip = pyodide.pyimport('micropip')
        console.log(pyodide._api.sys.version)

        let requirements = this.config.requirements
        if (!Array.isArray(requirements)) requirements = requirements()
        await Promise.all(requirements.map(this.pip.install))

        await this._load_env()

        if (this.__version__ === 'dev') {
            await this.pip.install(`${this.dev_path}/dist/beepy_web-0.0a0-py3-none-any.whl`)
        } else {
            await this.pip.install(`beepy_web==${this.__version__}`)
        }

        this.globals = this.python_api.run(
            'from beepy.utils.internal import _init_js, _BeePyGlobals;_init_js();_BeePyGlobals(globals())'
        )

        await this._main()
        this.dev_server.init()
    }
}

export const beepy = new BeePy(window.beepy || {})

window.addEventListener(
    window.navigator.webdriver ? 'beepy::server_side:load' : 'load',
    () => beepy._load(),
)
