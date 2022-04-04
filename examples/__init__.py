from pyweb import Tag, mount, state, attr, on
from pyweb.style import style
from pyweb.tags import br


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

    children = [
        PyButton(title='+', color='red'),
        PyButton(title='–', increment=-1),
    ]

    def content(self):
        # TODO: maybe parse \n as <br>?
        return f'{self.title}{br}Count: {self.count}'


mount(
    View(title='PyWeb Test 2'),
    '#pyweb',
)
