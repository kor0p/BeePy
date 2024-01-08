import {_lstrip} from './utils'

export const rootFolder = '__beepy_root__'


export class Files {
    static _lastLoadedFile = ''

    static mkDirPath (path, removeFileName=false) {
        const pathParts = path.split('/')
        let maxLength = pathParts.length
        if (removeFileName) maxLength -= 1

        for (let length = 1; length <= maxLength; length++) {
            let pathToCreate = rootFolder + '/' + pathParts.slice(0, length).join('/')
            if (!pyodide.FS.analyzePath(pathToCreate).exists) pyodide.FS.mkdir(pathToCreate)
        }
    }

    static _parseAndMkDirFile (filePath, addCurrentPath = false, separator='/') {
        let path = ''

        if (filePath && filePath.indexOf(separator) !== -1) {
            let pathParts = filePath.split(separator).reverse()
            filePath = pathParts.shift()
            path = pathParts.reverse().join('/')
            this.mkDirPath(path)
        }

        if (addCurrentPath) {
            return [this.populateCurrentPath(path), filePath, path]
        }

        return [path, filePath]
    }


    static _parseAndMkDirModule (module, addCurrentPath) {
        return this._parseAndMkDirFile(module, addCurrentPath, '.')
    }

    static populateCurrentPath (path) {
        const currentPath = this._lastLoadedFile.replace(/(\/(\w*.py)?)*$/, '')
        return `${currentPath}${currentPath && path ? '/' : ''}${path.replace(/^\/*/, '')}`
    }

    static getPathWithCurrentPathAndOrigin (path) {
        path = this.populateCurrentPath(path)
        if (!path.includes('http')) path = `${window.location.origin}/${path}`
        return path
    }
}


export class SyncFiles {
    static loadFile (filePath) {
        filePath = _lstrip(filePath)
        Files._lastLoadedFile = filePath
        if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`

        const req = new XMLHttpRequest()
        req.open('GET', filePath, false)
        req.send(null)
        if (req.status >= 400 && req.status < 500) {
            throw new Error('File not found')
        }
        return req.response
    }

    static _writeFile (file, content) {
        if (!content) content = this.loadFile(file)
        pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
    }
}


export class AsyncFiles {
    static async loadFile (filePath) {
        Files._lastLoadedFile = filePath
        if (!filePath.includes('http')) filePath = `${window.location.origin}/${filePath}`

        const r = await fetch(filePath, {method: 'GET'})
        if (r.status >= 400 && r.status < 500) {
            throw new Error('File not found')
        }
        return await r.text()
    }

    static async _writeFile (file, content) {
        if (!content) content = await this.loadFile(_lstrip(file))
        pyodide.FS.writeFile(`${rootFolder}/${file}`, content)
    }
}
