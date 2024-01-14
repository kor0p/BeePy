import {AsyncFiles, rootFolder} from './files'
import {python} from './python'


class DevServer {
    started = false
    _filePathToModuleAndRealFileCache = {}

    init () {
        if (!beepy.config.development) return

        try {  // TODO: add flag parameter for this
            this.ws = new WebSocket('ws://localhost:8998/')
            this.started = true
        } catch (e) {
            return  // Dev Hot Reload server is not started
        }

        python.run('import importlib as _dev_importlib; import sys as _dev_sys')
        this.ws.onmessage = (...args) => this._handler(...args)
    }

    async _handler ({ data: file }) {
        if (file === '__') {  // dev mode
            return await beepy._main({reload: true})
        }

        const data = this._filePathToModuleAndRealFileCache[file]
        if (data) {
            const [fileToWrite, module] = data
            if (module) {
                await AsyncFiles._writeFile(fileToWrite, await AsyncFiles.loadFile(file))
                await python.runAsync(`_dev_importlib.reload(_dev_sys.modules['${module}'])`)
            }
        }
        await python.runAsync(`_dev_importlib.reload(_dev_sys.modules['${rootFolder}'])`)
        await beepy._main({reload: true})
    }
}

export const dev_server = new DevServer()
