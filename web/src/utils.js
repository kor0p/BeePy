export function _debugger (error=null) {
    const place_breakpoint_here = 'use variable _locals in console to get locals() from python frame'
}
window._DEBUGGER = _debugger


Element.prototype.insertChild = function (child, index) {
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

Element.prototype.safeRemoveChild = function (child) {
    if (this.contains(child)) {
        return this.removeChild(child)
    }
}

Element.prototype.__str__ = function () {
    return `<${this.tagName.toLowerCase()}/>`
}

export function addHTMLElement (mountPoint, elementName, options={}) {
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

export function isObjectEmpty(obj) {
    return Object.keys(obj).length === 0;
}

export function isObject (obj) {
    return obj && typeof obj === 'object'
}

export function mergeDeep(...objects) {
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

window.delay = async function delay(ms) {
    return new Promise(r => setTimeout(r, ms))
}


export function _lstrip (text) {
    return text.replace(/^\/+/, '')
}

export function get_meta (name) {
    const el = document.querySelector(`meta[name="${name}"]`)
    return el ? el.content : ''
}

export const _py_tag_attribute = '__PYTHON_TAG__'

function getPyTag(i) {
    /**
     * usage:
     * > py0
     * evaluates $0.__PYTHON_TAG__
     * available for py0-py9
     */
    return () => window[`$${i}`][_py_tag_attribute]
}

Object.defineProperties(
    window,
    Object.fromEntries(new Array(10).fill(null).map(
        (_, i) => [`py${i}`, {get: getPyTag(i)}]
    ))
)
