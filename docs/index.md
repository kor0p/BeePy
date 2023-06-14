# PyWeb
### The _frontend_ web framework for Python

## How?
### Thanks for [pyodide](https://pyodide.org/), written in [WASM](https://webassembly.org/).

## Why?
### Use Python in browser to build modern frontend via PyWeb!

## 🚀 Getting started
<script src='https://kor0p.github.io/PyWeb/pyweb.js'></script>
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
pyweb.__main__ = () => apy(document.getElementById('id-getting-started').innerText)
// ]]>
</script>
:::

::::