from beepy import Directive, Style, Tag
from beepy.tags import input_


class Focus(Directive, name='focus'):
    def render(self):
        self.mount_element.focus()


class App(Tag, name='div'):
    style = Style(
        zoom=4,
        margin='8px',
        input={
            'border-radius': '0.3rem',
            '&:focus': {
                'outline': '0.1rem solid limegreen',
            },
        },
    )

    children = [
        input_(placeholder='Input text...', children=[Focus()]),
    ]

    def content(self):
        return 'This input is in focus)'
