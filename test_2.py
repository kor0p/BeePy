# [PYWEB IGNORE START]
from pyweb import *
# [PYWEB IGNORE END]


class PyButton(Tag, name='button'):
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
