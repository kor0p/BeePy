# PyWeb v0.1.1b

## A frontend framework for python, using [pyodide](https://pyodide.org/), that uses [WASM](https://webassembly.org/)
### Use classes, descriptors and rest python in browser!

## examples
> ### Netlify static pages:
> - ### [First try](https://pyweb.netlify.app/examples/)
> - ### [Tabs](https://pyweb.netlify.app/examples/tabs/)

Code:
```python
# examples/1.py
# [PYWEB IGNORE START]
from pyweb import Tag, mount, state, attr, on, style, br
# [PYWEB IGNORE END]


class PyButton(Tag, name='button'):
    parent: 'View'

    test: bool = attr(True)

    title: str = state()
    increment: int = state(1)
    color: str = state('gray')

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
    count: int = attr(0)

    title: str = state()

    style = style(
        zoom=7,
        button=dict(backgroundColor='lightblue')
    )

    button_inc = PyButton(title='+', color='red')
    button_dec = PyButton(title='–', increment=-1)

    def content(self):
        return (
            self.title,
            br,
            'Count: ', self.count
        )


mount(
    View(title='PyWeb Test 2'),
    '#pyweb',
)

```
will render html as below, and will react on buttons click like native JS
```html
<head>
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
