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
        # TODO: maybe parse \n as <br>?
        return f'{self.title}{br}Count: {self.count}'

    def mount(self):
        Head.title = 'Test 1'


if __name__ == '__pyweb_root__':
    mount(View(), '#root')
