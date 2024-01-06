from beepy import Style, Tag, Directive, state, on
from beepy.tags import change, p
from beepy.style import Var


class Highlight(Directive, name='highlight'):
    color = state('', model='change')

    @on
    def mouseenter(self):
        self.set_highlight(self.color)

    @on
    def mouseleave(self):
        self.set_highlight(None)

    @color.on('change')
    def set_highlight(self, new_color):
        self.parent.style_highlight.var('highlight_color', new_color)


class App(Tag, name='div'):
    style = Style(
        zoom=4,
        display='block',
        padding='8px',
        input={
            'border-radius': '0.3rem',
        },
    )

    style_highlight = Style(
        p={
            'backgroundColor': Var('highlight_color'),
        }
    )

    color = state('red')

    highlight = Highlight(element='text', color=color)

    children = [
        change(value=color),
        text := p('Hover me')
    ]

    def content(self):
        return f'Current color: {self.color}'
