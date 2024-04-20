from beepy import Style, Tag, attr, on, state
from beepy.tags import Head

Head.title = 'Colored Increment Buttons'


class ColoredButton(Tag, name='button'):
    parent: 'View'

    some_attr = attr(default=True)

    title = state('')
    increment = state(1)
    color = state('gray')

    style = Style(
        styles={
            '&': {
                'margin': '8px',
            },
            '& *': {
                'color': '{color}',
            },
        },
    )

    @on
    def click(self):
        self.parent.count += self.increment

    def content(self):
        return self.title


class View(Tag, name='view'):
    count = attr(0)

    title = state('Increment buttons example')

    style = Style(zoom=7, width='25px', height='25px')

    children = [
        ColoredButton(title='+', color='red'),
        ColoredButton(title='-', increment=-1),
    ]

    def content(self):
        return f'{self.title}\nCount: {self.count}'
