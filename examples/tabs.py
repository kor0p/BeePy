from pyweb import Tag, Style, mount, attr, state, __version__
from pyweb.tags import button, p, select, Head
from pyweb.tabs import tab, tab_title, tabs
from pyweb.types import safe_html


class View(Tag, name='view'):
    class PyButton(button):
        color = state('gray')

        style = Style(
            margin='8px',
            color='{color}',
        )

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

    select = select.with_items(items)

    children = [
        select,
    ]

    def mount(self):
        self.select.select(self.selected)

    @select.on
    def change(self, event):
        self.selected = event.target.value

    def content(self):
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
        safe_html(f'''
        <p>
            PyWeb (version {__version__})<br>
            A frontend framework for python, using <a href="https://pyodide.org/" target="_blank">pyodide</a>
            via <a href="https://webassembly.org/">WebAssembly</a>
        </p>
        <p>
            More examples:<br>
            <a href="/examples/buttons" target="_blank">First try</a><br>
            <a href="/examples/" target="_blank">Tabs (this one)</a><br>
            <a href="/examples/todos" target="_blank">Todo List</a><br>
            <a href="/examples/modal" target="_blank">Modal</a><br>
            <a href="/examples/context-menu" target="_blank">Context Menu</a><br>
            <a href="/examples/dynamic-url" target="_blank">Dynamic URL</a><br>
            <a href="/examples/timer" target="_blank">Timer</a><br>
            <a href="/examples/text-sync" target="_blank">Input's model</a><br>
        </p>
        <p>
            Made by <a href="https://t.me/kor0p" target="_blank">© kor0p</a><br>
            Source code of PyWeb: <a href="https://github.com/kor0p/PyWeb" target="_blank">GitHub</a>
        </p>
        ''')
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
