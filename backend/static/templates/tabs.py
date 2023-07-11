from functools import partial

from beepy import Tag, Style, attr, state, __version__
from beepy.tags import button, a, p, i, span, select, Head, ul
from beepy.modules.tabs import tab, tab_title, tabs
from beepy.router import WithRouter, Link


Head.title = 'Tabs example'
a_nt = partial(a, target='_blank')
NEW_LINE = span('\n')


class ColoredButton(button):
    color = state('gray')

    style = Style(
        margin='8px',
        color='{color}',
    )


class ButtonsView(Tag):
    count = attr(0)

    style = Style(
        button=dict(
            backgroundColor='lightblue',
        )
    )

    children = [
        button_inc := ColoredButton('+', color='red'),
        button_dec := ColoredButton('–'),
    ]

    @button_inc.on('click')
    def increment(self, event):
        self.count += 1

    @button_dec.on('click')
    def decrement(self, event):
        self.count -= 1

    def content(self):
        return ('Colored Increment Buttons\nCount: ', self.count)


class SelectView(Tag, name='div', content_tag='span'):
    selected = attr('1')

    items = {'0': 'first', '1': 'second', '2': 'third'}

    children = [
        select := select.with_items(items, value=selected),
    ]

    def content(self):
        # TODO: maybe create decorator @content() with parameters?
        # TODO: think about better syntax?
        return [
            p(lambda _: f'Key: {self.selected}'),
            p(lambda _: f'Value: {self.items[self.selected]}')
        ]


class ExamplesTabs(tabs):
    dark_theme = True
    name = 'ex'

    children = [
        tabs_titles := ul(
            main=tab_title('Examples'),
            buttons=tab_title('Increment Buttons'),
            selector=tab_title('Selector '),
        ),
        main := tab(
            p(
                span(f'\N{honeybee} BeePy v{__version__}'),
                NEW_LINE,
                span('The '),
                i('frontend'),
                span(' framework for python, using '),
                a_nt('Pyodide', href='https://pyodide.org/'),
                span(' via '),
                a_nt('Emscripten', href='https://emscripten.org/'),
                span(' and '),
                a_nt('WebAssembly', href='https://webassembly.org/'),
            ),
            p(
                span('More examples:'),
                NEW_LINE,
                Link('Admin panel (Django)', to='admin'),
                NEW_LINE,
                a_nt('BeePy Sandbox', href='https://kor0p.github.io/BeePy/examples/sandbox/'),
                NEW_LINE,
                Link('Dynamic plot', to='plot'),
                NEW_LINE,
                Link('First try', to='buttons'),
                NEW_LINE,
                Link('Tabs (this one)', to=''),
                NEW_LINE,
                Link('Todo List', to='todos'),
                NEW_LINE,
                Link('Modal', to='modal'),
                NEW_LINE,
                Link('Context Menu', to='context-menu'),
                NEW_LINE,
                Link('Dynamic URL', to='dynamic-url'),
                NEW_LINE,
                Link('Timer', to='timer'),
                NEW_LINE,
                Link('Input\'s model', to='text-sync'),
                NEW_LINE,
                a_nt('Multiple apps on one page', href='/multiple-apps'),
                NEW_LINE,
                a_nt('Just the other one example', href='/custom_url'),
                NEW_LINE,
            ),
            p(
                span('Made by '),
                a_nt('© kor0p', href='https://t.me/kor0p'),
                NEW_LINE,
                span('Source code of BeePy: '),
                a_nt('GitHub', href='https://github.com/kor0p/BeePy'),
            ),
        ),
        buttons := tab(
            ButtonsView(),
        ),
        selector := tab(
            SelectView(),  # TODO: check why duplicating this view cause problems with <select>
        ),
    ]


class View(Tag, WithRouter):
    style = Style(
        color='white',
        zoom=4,
        font_size='12px',
    )

    children = [
        ExamplesTabs(),
    ]
