# PyWeb v0.0.2b

## A frontend framework, written in python, using [pyodide](https://pyodide.org/), that uses [WASM](https://webassembly.org/)
### Use classes, descriptors and rest python in browser!

## examples
> ### Netlify static pages:
> - ### [First try](https://pyweb.netlify.app/)

Code:
```python
# examples/1.py
# [PYWEB IGNORE START]
from pyweb import Tag, mount, state, attr, on, style, div, br
# [PYWEB IGNORE END]


class PyButton(Tag, name='button'):
    parent: 'View'

    title: str = state()
    increment: int = state(1)
    color: str = state('gray')
    test: bool = attr(True)

    style = style(
        margin='8px',
        color='%(color)s',
    )

    @on
    def click(self, event):
        self.parent.count += self.increment

    def content(self):
        return self.title


class View(div, name='view'):
    title: str = state()
    count: int = attr(0)

    style = style(
        color='white',
        zoom=7,
        button=dict(
            backgroundColor='lightblue',
        )
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
<body>
    <div id="pyweb">
        <view count="0" style-id="62Ldyb....">
            <div>PyWeb Test 2<br>Count: 0</div>
            <style>
                view[style-id="62Ldyb...."] {
                    color: white;
                    zoom: 7;
                }
                view[style-id="62Ldyb...."] button {
                    background-color: lightblue;
                }
            </style>
            <button test style-id="BdGmbd....">
                <div>+</div>
                <style>
                    button[style-id="BdGmbd...."] {
                        margin: 8px;
                        color: red;
                    }
                </style>
            </button>
            <button test style-id="cGrw7s....">
                <div>–</div>
                <style>
                    button[style-id="cGrw7s...."] {
                        margin: 8px;
                        color: gray;
                    }
                </style>
            </button>
        </view>
    </div>
</body>
```
