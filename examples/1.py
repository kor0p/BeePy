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
