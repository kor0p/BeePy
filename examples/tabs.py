# [PYWEB IGNORE START]
from pyweb import Tag, mount, style, div, a, p, select, br, attr, state, on
from pyweb.tabs import tab, tab_title, tabs
# [PYWEB IGNORE END]


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
        color='white',
        button=dict(backgroundColor='lightblue')
    )

    button_inc = PyButton(title='+', color='red')
    button_dec = PyButton(title='–', increment=-1)

    def content(self):
        return (
            self.title,
            br,
            'Count: ', self.count
        )


class SelectView(Tag, name='div', content_tag=None):
    selected: str = attr('1')

    items = {'0': 'first', '1': 'second', '2': 'third'}

    def mount(self):
        self.select.onchange = self.onchange

    def onchange(self, value):
        self.selected = value

    def content(self):
        return [
            p(lambda _: f'Key: {self.selected}'),
            p(lambda _: f'Value: {self.items[self.selected]}')
        ]

    select = select.with_items(items, selected='1')


class LinkTabs(tabs):
    name = 'TEST'
    tabs_titles = {
        'tab_text': tab_title('Page 1'),
        'tab_buttons': tab_title('Page 2'),
        'tab_selector': tab_title('Page 3'),
    }

    tab_text = tab(
        '''
        <p>
            A frontend framework for python, using <a href="https://pyodide.org/" target="_blank">pyodide</a>,
            that uses <a href="https://webassembly.org/">WebAssembly</a>
        </p>
        <p>Made by <a href="https://t.me/kor0p" target="_blank">© kor0p</a></p>
        <p>Source code of PyWeb: <a href="https://github.com/kor0p/PyWeb" target="_blank">GitHub</a></p>
        <p>Version 0.1.0 beta</p>
        '''
    )
    tab_buttons = tab(
        View(title='PyWeb Test 2'),
    )
    tab_selector = tab(
        SelectView(),
    )


class test_tabs(Tag, name='test-tabs'):
    style = style(
        color='white',
        zoom=5,
    )

    tabs = LinkTabs()


test = test_tabs()


mount(
    test,
    '#pyweb',
)
