from __future__ import annotations


import js

from beepy.framework import Tag, attr, state, on
from beepy.style import Style
from beepy.tags import div
from beepy.utils import to_js


class tab(div, name='tab'):
    tab_id = state(type=str)
    visible = attr(False)
    title: tab_title = state()

    default_style = Style(styles={
        'padding': '6px 12px',
        'animation': 'fadeEffect 1s',
        'display': 'none',
        '&[visible]': {
            'display': 'block',
        }
    })

    @attr()
    def id(self) -> str:
        return f'tab-{self.parent.name}/{self.tab_id}'

    parent: tabs

    def __set_ref__(self, parent, ref):
        super().__set_ref__(parent, ref)
        self.tab_id = ref.name


class tab_title(Tag, name='li', content_tag=None):
    _tab: tab = state(type=tab)
    selected = attr(False)

    @on
    def click(self, event):
        self._tab.parent.select_tab(self._tab.tab_id)


class tabs(Tag, name='tabs', content_tag='ul'):
    dark_theme = attr(False)
    selected_id = attr(type=str)
    selected: tab = state(type=tab)

    name: str = 'Unknown'
    tabs_titles: dict = {
        # id: tab_title(text),
    }

    default_style = Style(styles={
        'a': {
            'color': 'lightskyblue',
            'text-decoration': 'none',
        },
        'ul': {
            '': '''
            list-style-type: none;
            margin: 0;
            padding: 0;
            overflow: hidden;
            background-color: #e1e1e1;
            ''',
            'li': {
                '': '''
                float: left;
                font-family: "Lato", sans-serif;
                display: inline-block;
                text-align: center;
                padding: 14px 16px;
                text-decoration: none;
                transition: 0.3s;
                font-size: 12px;
                ''',
                '&:hover': {
                    'background-color': '#cdcdcd',
                },
                '&[selected]': {
                    'background-color': '#b1b1b1',
                },
            },
        },
        '&[dark-theme] ul': {
            'background-color': '#1e1e1e',
            'li': {
                '&:hover': {
                    'background-color': '#222222',
                },
                '&[selected]': {
                    'background-color': '#3e3e3e',
                },
            },
        },
    })

    @property
    def tabs_list(self) -> dict[str, tab]:
        # TODO: make tabs_list one-time calculated attribute
        return {name: _tab for name, _tab in self.ref_children.items() if isinstance(_tab, tab)}

    def content(self):
        return [title for title in self.tabs_titles.values()]

    def mount(self):
        for tab_id, tab in self.tabs_list.items():
            title = self.tabs_titles[tab_id]
            title._tab = tab
            title.link_parent_attrs(self)
            tab.title = title

        url = js.URL.new(js.location.href)

        selected = None
        if url.hash and url.hash.startswith(f'#tab-{self.name}/'):
            selected = self.select_tab(url.hash[len(f'#tab-{self.name}/'):])
            if selected:
                js.location.hash = ''
        if not selected:
            selected = self.select_tab(url.searchParams.get(self.name))
        if not selected:
            self.select_tab(tuple(self.tabs_titles.keys())[0])

    def select_tab(self, tab_id):
        if not tab_id or not hasattr(self, tab_id):
            return

        self.selected_id = tab_id
        if not self.selected or self.selected.tab_id != tab_id:
            for child in self.tabs_list.values():
                child.visible = False
            for title in self.tabs_titles.values():
                title.selected = False
            self.selected = getattr(self, tab_id)
            self.selected.visible = True
            self.tabs_titles[tab_id].selected = True

        return self.selected

    def _update_url(self):
        selected_tab = self.selected

        url = js.URL.new(js.location.href)
        if (not url.hash and url.href[-1] == '#') or url.hash == '#':
            url.href = url.href[:-1]
        if url.searchParams.get(self.name) == selected_tab.tab_id:
            return

        url.searchParams.set(self.name, selected_tab.tab_id)  # modifies url.href

        js.history.pushState(
            to_js({
                'name': selected_tab.id,
                'title': ''.join(selected_tab.title.content()),
            }),
            selected_tab.id,
            url.href,
        )

    def render(self):
        self._update_url()


__all__ = ['tab', 'tab_title', 'tabs']
