# 🐝 BeePy
### The _frontend_ web framework for Python

## How?
### Thanks for [Pyodide](https://pyodide.org/) - port of Python to [Emscripten](https://emscripten.org/), based on [WASM](https://webassembly.org/).

## Why?
### Use Python in browser to build modern frontend via BeePy!

<script src='https://kor0p.github.io/BeePy/beepy.js'></script>
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