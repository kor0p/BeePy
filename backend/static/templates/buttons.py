from beepy import Tag, Style, state, attr, on
from beepy.tags import Head

Head.title = 'Test 1'


class PyButton(Tag, name='button'):
    parent: 'View'

    test = attr(True)

    title = state('')
    increment = state(1)
    color = state('gray')

    style = Style(styles={
        '&': {
            'margin': '8px',
        },
        '& *': {
            'color': '{color}',
        }
    })

    @on
    def click(self, event):
        self.parent.count += self.increment

    def content(self):
        return self.title


class View(Tag, name='view'):
    count = attr(0)

    title = state('Increment buttons example')

    style = Style(
        zoom=7,
    )

    children = [
        PyButton(title='+', color='red'),
        PyButton(title='–', increment=-1),
    ]

    def content(self):
        return f'{self.title}\nCount: {self.count}'
