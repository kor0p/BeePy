# 🐝 BeePy
### The _frontend_ web framework for Python

## How?
### Thanks for [Pyodide](https://pyodide.org/) - port of Python to [Emscripten](https://emscripten.org/), based on [WASM](https://webassembly.org/).

## Why?
### Use Python in browser to build modern frontend via BeePy!

## Local development:
### Firstly, install BeePy
### `pip install -U beepy-web[dev]`
### Then, add `index.html` and `__init__.py` to root of project
### and start local server at same directory
### `python -m beepy.dev`
### That's it!
### Now, click on link in console to visit your server
### and change code to see updates in browser in no time!

<script src='https://kor0p.github.io/BeePy/beepy.js?v=0.8.0'></script>
<script>
// <![CDATA[
beepy.__main__ = async () => {
    for (const demo_id of ['id-getting-started', 'id-synced-counters']) {
        await apy(document.getElementById(demo_id).innerText)
    }
}
// ]]>
</script>
## 🚀 Getting started
::::{tab-set}

:::{tab-item} main.py
(id-getting-started)=
```{literalinclude} demo/getting-started.py
:language: python
```
:::

:::{tab-item} 🎉 Result

<div id="demo-getting-started"></div>
:::

::::

## Synced Counters
::::{tab-set}

:::{tab-item} main.py
(id-synced-counters)=
```{literalinclude} demo/synced-counters.py
:language: python
```
:::

:::{tab-item} 🎉 Result

<div id="demo-synced-counters"></div>
:::

::::
