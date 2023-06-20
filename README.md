# 🐝 BeePy

## The _frontend_ web framework for python 
### Thanks for [Pyodide](https://pyodide.org/) - port of Python to [Emscripten](https://emscripten.org/), based on [WASM](https://webassembly.org/).
### Use Python in browser to build modern frontend via BeePy!

## Try it out! [CodeSandBox](https://codesandbox.io/s/beepy-two-synced-counters-k5sm9j) and [BeePy Sandbox](https://kor0p.github.io/BeePy/examples/sandbox/)

## Join our community at [Telegram chat](https://t.me/bee_py/)

Code (custom_url.py from examples):
```python
from beepy import Tag, mount, state, on

class IncrementButton(Tag, name='button'):
    count = state(0)

    @on
    def click(self, event):
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
- [List of examples (with Tabs)](https://beepy.herokuapp.com/e/)
- [Admin panel](https://beepy.herokuapp.com/e/admin)
- [Dynamic plot](https://beepy.herokuapp.com/e/plot)
- [First try](https://beepy.herokuapp.com/e/buttons)
- [Todo List](https://beepy.herokuapp.com/e/todos)
- [Modal](https://beepy.herokuapp.com/e/modal)
- [Context Menu](https://beepy.herokuapp.com/e/context-menu)
- [Dynamic URL](https://beepy.herokuapp.com/e/dynamic-url)
- [Timer](https://beepy.herokuapp.com/e/timer)
- [Input's model](https://beepy.herokuapp.com/e/text-sync)
- [Multiple apps on one page](https://beepy.herokuapp.com/multiple-apps)
- [Just the other one example](https://beepy.herokuapp.com/e/custom_url)
- [BeePy Sandbox](https://kor0p.github.io/BeePy/examples/sandbox/)
