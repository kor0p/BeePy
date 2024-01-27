import {Files, rootFolder} from './files'
import {python} from './python'


class DevServer {
    started = false
    _filePathToModuleAndRealFileCache = {}

    init () {
        if (!beepy.config.development) return

        this._globals = python.run('{}')
        try {  // TODO: add flag parameter for this
            this.ws = new WebSocket('ws://localhost:8998/')
            this.started = true
        } catch (e) {
            return  // Dev Hot Reload server is not started
        }

        python.run('import importlib, sys', {globals: this._globals})
        this.ws.onmessage = (...args) => this._handler(...args)
    }

    async _reload_module (module_name) {
        await this._globals.get('importlib').reload.callSyncifying(this._globals.get('sys').modules.get(module_name))
    }

    async _handler ({ data: file }) {
        const data = this._filePathToModuleAndRealFileCache[file]
        if (data) {
            const [fileToWrite, module] = data
            if (module) {
                await Files.writeFile(fileToWrite, await Files.loadFile(file))
                await this._reload_module(module)
            }
            await this._reload_module(rootFolder)
        }
        await beepy._main({reload: true})
    }
}

export const dev_server = new DevServer()
