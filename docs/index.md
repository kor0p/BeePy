# BeePy
### The _frontend_ web framework for Python

## How?
### Thanks for [Pyodide](https://pyodide.org/) - port of Python to [Emscripten](https://emscripten.org/), based on [WASM](https://webassembly.org/).

## Why?
### Use Python in browser to build modern frontend via BeePy!

## 🚀 Getting started
<script src='https://kor0p.github.io/BeePy/beepy.js'></script>
::::{tab-set}

:::{tab-item} main.py
(id-getting-started)=
```{literalinclude} demo/getting-started.py
:language: python
```
:::

:::{tab-item} 🎉 Result

<div id="demo-getting-started"></div>
<script>
// <![CDATA[
beepy.__main__ = () => apy(document.getElementById('id-getting-started').innerText)
// ]]>
</script>
:::

::::