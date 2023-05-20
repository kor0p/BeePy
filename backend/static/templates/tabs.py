from functools import partial

from pyweb import Tag, Style, attr, state, __version__
from pyweb.tags import button, a, p, span, select, Head
from pyweb.tabs import tab, tab_title, tabs
from pyweb.router import WithRouter, Link


Head.title = 'Tabs example'
a_nt = partial(a, target='_blank')
NEW_LINE = span('\n')


class PyButton(button):
    color = state('gray')

    style = Style(
        margin='8px',
        color='{color}',
    )


class View(Tag, name='view'):

    count = attr(0)

    title = state('')

    style = Style(
        button=dict(
            backgroundColor='lightblue',
        )
    )

    button_inc = PyButton('+', color='red')
    button_dec = PyButton('–')

    children = [
        button_inc,
        button_dec,
    ]

    @button_inc.on('click')
    def increment(self, event):
        self.count += 1

    @button_dec.on('click')
    def decrement(self, event):
        self.count -= 1

    def content(self):
        return (
            self.title,
            '\nCount: ',
            self.count,
        )


class SelectView(Tag, name='div', content_tag='span'):
    selected = attr('1')

    items = {'0': 'first', '1': 'second', '2': 'third'}

    select = select.with_items(items, value=selected)

    children = [
        select,
    ]

    def content(self):
        # TODO: maybe create decorator @content() with parameters?
        # TODO: think about better syntax?
        return [
            p(lambda _: f'Key: {self.selected}'),
            p(lambda _: f'Value: {self.items[self.selected]}')
        ]


class LinkTabs(tabs):
    dark_theme = True
    name = 'TEST'
    tabs_titles = {
        'tab_text': tab_title('Page 1'),
        'tab_buttons': tab_title('Page 2'),
        'tab_selector': tab_title('Page 3'),
    }

    tab_text = tab(
        p(
            span(f'PyWeb (version {__version__})'),
            NEW_LINE,
            span('A frontend framework for python, using '),
            a_nt('pyodide', href='https://pyodide.org/'),
            span(' via '),
            a_nt('WebAssembly', href='https://webassembly.org/'),
        ),
        p(
            span('More examples:'),
            NEW_LINE,
            Link('Admin panel (Django)', to='admin'),
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
            a_nt('Custom url, hosted by Django', href='/custom_url'),
            NEW_LINE,
        ),
        p(
            span('Made by '),
            a_nt('© kor0p', href='https://t.me/kor0p'),
            NEW_LINE,
            span('Source code of PyWeb: '),
            a_nt('GitHub', href='https://github.com/kor0p/PyWeb'),
        ),
    )
    tab_buttons = tab(
        View(title='PyWeb Test 2'),
    )
    tab_selector = tab(
        SelectView(),  # TODO: check why duplicating this view cause problems with <select>
    )

    children = [
        tab_text,
        tab_buttons,
        tab_selector,
    ]


class test_tabs(Tag, WithRouter, name='test-tabs'):
    style = Style(
        color='white',
        zoom=4,
        font_size='12px',
    )

    children = [
        LinkTabs(),
    ]
