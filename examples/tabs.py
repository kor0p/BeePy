from functools import partial

from pyweb import Tag, Style, mount, attr, state, __version__
from pyweb.tags import button, a, p, span, select, Head
from pyweb.tabs import tab, tab_title, tabs


a_nt = partial(a, target='blank')
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
            a_nt('First try', href='/examples/buttons'),
            NEW_LINE,
            a_nt('Tabs (this one)', href='/examples/'),
            NEW_LINE,
            a_nt('Todo List', href='/examples/todos'),
            NEW_LINE,
            a_nt('Modal', href='/examples/modal'),
            NEW_LINE,
            a_nt('Context Menu', href='/examples/context-menu'),
            NEW_LINE,
            a_nt('Dynamic URL', href='/examples/dynamic-url'),
            NEW_LINE,
            a_nt('Timer', href='/examples/timer'),
            NEW_LINE,
            a_nt('Input\'s model', href='/examples/text-sync'),
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


class test_tabs(Tag, name='test-tabs'):
    style = Style(
        color='white',
        zoom=4,
        font_size='12px',
    )

    children = [
        LinkTabs(),
    ]

    def mount(self):
        Head.title = 'Tabs example'


if __name__ == '__pyweb_root__':
    mount(test_tabs(), '#root')
