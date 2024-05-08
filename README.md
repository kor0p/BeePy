# 🐝 BeePy

[![NPM Package](https://img.shields.io/npm/v/@kor0p/beepy)](https://www.npmjs.com/package/@kor0p/beepy)
[![PyPI Package](https://img.shields.io/pypi/v/beepy-web.svg)](https://pypi.org/project/beepy-web/)
[![Documentation](https://cdn.jsdelivr.net/gh/Andre601/devins-badges@v3.x-mkdocs-material/assets/compact-minimal/built-with/mkdocs-material_vector.svg)](https://bee-py.readthedocs.io/en/latest/)

## The _frontend_ web framework for python
### Thanks for [Pyodide](https://pyodide.org/) - port of Python to [Emscripten](https://emscripten.org/), based on [WASM](https://webassembly.org/).
### Use Python in browser to build modern frontend via BeePy!

## Try it out! [CodeSandBox](https://codesandbox.io/s/beepy-two-synced-counters-k5sm9j) and [BeePy Sandbox](https://kor0p.github.io/BeePy-examples/sandbox)

## Join our community at [Telegram chat](https://t.me/bee_py/)
## [Documentation](https://kor0p.github.io/BeePy-examples/sandbox) | [PyPI](https://pypi.org/project/beepy-web/) | [NPM](https://www.npmjs.com/package/@kor0p/beepy)

## Local development:
### Install BeePy
### `pip install -U beepy-web[dev]`
### Then just start local server
### `beepy dev --init`
### And that's it!

### Now, click on link in console to visit your server
### and change code to see updates in browser in no time!

Code (custom_url.py from examples):
```python
from beepy import Tag, mount, state, on

class IncrementButton(Tag, name='button'):
    count = state(0)

    @on
    def click(self):
        self.count += 1

    def content(self):
        return f'Count: {self.count}'

mount(IncrementButton(), '#root')
```
will render html as below, and will react on buttons click like native JS
```html
<body>
    <div id="root">
        <button>
            <div>Count: 5</div>
        </button>
    </div>
</body>
```

## Examples:
- [List of examples (with Tabs)](https://beepy-web-ba63e5a12994.herokuapp.com/e/)
- [Admin panel](https://beepy-web-ba63e5a12994.herokuapp.com/e/admin)
- [Dynamic plot](https://beepy-web-ba63e5a12994.herokuapp.com/e/plot)
- [First try](https://beepy-web-ba63e5a12994.herokuapp.com/e/buttons)
- [Todo List](https://beepy-web-ba63e5a12994.herokuapp.com/e/todos)
- [Modal](https://beepy-web-ba63e5a12994.herokuapp.com/e/modal)
- [Context Menu](https://beepy-web-ba63e5a12994.herokuapp.com/e/context-menu)
- [Dynamic URL](https://beepy-web-ba63e5a12994.herokuapp.com/e/dynamic-url)
- [Timer](https://beepy-web-ba63e5a12994.herokuapp.com/e/timer)
- [Input's model](https://beepy-web-ba63e5a12994.herokuapp.com/e/text-sync)
- [Multiple apps on one page](https://beepy-web-ba63e5a12994.herokuapp.com/multiple-apps)
- [Just the other one example](https://beepy-web-ba63e5a12994.herokuapp.com/e/custom_url)
- [BeePy Sandbox](https://kor0p.github.io/BeePy-examples/sandbox)
