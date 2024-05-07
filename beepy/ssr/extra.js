window.__update_config_obj = function (newConfig) {
    for (const [name, value] of Object.entries(newConfig)) {
        window.beepy.config[name] = value
    }
}

window.__add_meta_config_elements = function (elements) {
    for (const [name, content] of Object.entries(elements)) {
        const el = document.createElement('meta')
        document.head.insertBefore(el, document.head.children[0])
        el.outerHTML = `<meta name="beepy::config:${name}" content="${content}">`
    }
}
