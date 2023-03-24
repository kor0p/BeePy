# PyWeb v0.3.0

## A frontend framework for python, using [pyodide](https://pyodide.org/), that uses [WASM](https://webassembly.org/)
### Use classes, descriptors and rest python in browser!

## Netlify static examples:
- ### [First try](https://pyweb.netlify.app/examples/buttons)
- ### [Tabs](https://pyweb.netlify.app/examples/)
- ### [Todo List](https://pyweb.netlify.app/examples/todos)
- ### [Modal](https://pyweb.netlify.app/examples/modal)
- ### [Context Menu](https://pyweb.netlify.app/examples/context-menu)
- ### [Dynamic URL](https://pyweb.netlify.app/examples/dynamic-url)
- ### [Timer](https://pyweb.netlify.app/examples/timer)
- ### [Input's model](https://pyweb.netlify.app/examples/text-sync)

Code:
```python
# examples/buttons.py
from pyweb import Tag, mount, state, attr, on
from pyweb.style import style
from pyweb.tags import br, Head


class PyButton(Tag, name='button'):
    parent: 'View'

    test = attr(True)

    title = state('')
    increment = state(1)
    color = state('gray')

    style = style(
        margin='8px',
        color='{color}',
    )

    @on
    def click(self, event):
        self.parent.count += self.increment

    def content(self):
        return self.title


class View(Tag, name='view'):
    count = attr(0)

    title = state('PyWeb Test 2')

    style = style(
        zoom=7,
        button=dict(backgroundColor='lightblue')
    )

    children = [
        PyButton(title='+', color='red'),
        PyButton(title='–', increment=-1),
    ]

    def content(self):
        return f'{self.title}{br}Count: {self.count}'

    def mount(self):
        Head.title = 'Test 1'


if __name__ == '__pyweb_root__':
    mount(View(), '#pyweb')


```
will render html as below, and will react on buttons click like native JS
```html
<head>
    <title>Test 1</title>
    <style>
        view[style-id="6"] {
            zoom: 7;
        }
        view[style-id="6"] button {
            background-color: lightblue;
        }
    </style>
    <style>
        button[style-id="B"] {
            margin: 8px;
            color: red;
        }
    </style>
    <style>
        button[style-id="c"] {
            margin: 8px;
            color: gray;
        }
    </style>
</head>
<body>
    <div id="pyweb">
        <view count="0" style-id="6">
            <div>PyWeb Test 2<br>Count: 0</div>
            <button test style-id="B">
                <div>+</div>
            </button>
            <button test style-id="c">
                <div>–</div>
            </button>
        </view>
    </div>
</body>
```
