# PyWeb v0.3.3

## A frontend framework for python, using [pyodide](https://pyodide.org/), that uses [WASM](https://webassembly.org/)
### Use Python in browser to build modern frontend via PyWeb!

## Static examples:
- ### [List of examples (with Tabs)](https://pyweb.herokuapp.com/e/list-examples)
- ### [Admin panel](https://pyweb.herokuapp.com/e/)
- ### [Dynamic plot](https://pyweb.herokuapp.com/e/plot)
- ### [First try](https://pyweb.herokuapp.com/e/buttons)
- ### [Todo List](https://pyweb.herokuapp.com/e/todos)
- ### [Modal](https://pyweb.herokuapp.com/e/modal)
- ### [Context Menu](https://pyweb.herokuapp.com/e/context-menu)
- ### [Dynamic URL](https://pyweb.herokuapp.com/e/dynamic-url)
- ### [Timer](https://pyweb.herokuapp.com/e/timer)
- ### [Input's model](https://pyweb.herokuapp.com/e/text-sync)
- ### [Other page, served by Django](https://pyweb.herokuapp.com/e/custom_url)

Code (custom_url.py from examples):
```python
from pyweb import Tag, mount, state, on

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
