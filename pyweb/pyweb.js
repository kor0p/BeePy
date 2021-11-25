(async function () {
    if (!document.title) {
        document.title = 'PyWeb'
    }

    const script = document.createElement('script')
    script.type = 'application/javascript'
    script.src = 'https://cdn.jsdelivr.net/pyodide/v0.18.1/full/pyodide.js'

    document.head.appendChild(script)

    async function _load () {
        window.pyodide = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.18.1/full/' })
        window.py = pyodide.runPython
        window.apy = pyodide.runPythonAsync

        window.pyweb = {}
        pyweb.loadRawFile = async function loadRawFile (filePath) {
            return await (await fetch(filePath)).text()
        }
        pyweb.handleText = function handleText (text) {
            return text.replace(/# ?\[PYWEB IGNORE START\][^(\[PYWEB)]*# ?\[PYWEB IGNORE END\]/gm, '')
        }
        pyweb.loadFile = async function loadFile (filePath) {
            return pyweb.handleText(await pyweb.loadRawFile(filePath))
        }

        window.pyf = async function runPythonFile (filePath) {
            return window.py(await pyweb.loadFile(filePath))
        }
        window.apyf = async function runPythonAsyncFile (filePath) {
            return await window.apy(await pyweb.loadFile(filePath))
        }

    }

    window.addEventListener('load', async function () {
        await _load()
        py('import sys; print(sys.version)')

        // TODO: create wheel and load via pip
        for (const file of ['utils.py', 'framework.py', 'style.py', 'tags.py']) {
            await apyf(`pyweb/${file}`)
        }

        document.dispatchEvent(new Event('__PYWEB_LOADED__'))
    })
})()
