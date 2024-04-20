from __future__ import annotations

from boltons.iterutils import first

from beepy import Style, Tag, attr, attr_prop, html_attr, state
from beepy.tags import div, ul
from beepy.utils import js
from beepy.utils.js_py import replace_url


class tab(div, name='tab'):
    tab_id = state(type=str)
    visible = html_attr(default=False)
    title: tab_title = state()

    default_style = Style(
        styles={
            'padding': '6px 12px',
            'animation': 'fadeEffect 1s',
            'display': 'none',
            '&[visible]': {
                'display': 'block',
            },
        },
    )

    @attr_prop()
    def id(self) -> str:
        return f'tab-{self.parent.name}/{self.tab_id}'

    parent: tabs

    def _set_ref(self, parent, ref):
        super()._set_ref(parent, ref)
        self.tab_id = ref.name


class tab_title(Tag, name='li', content_tag=None):
    _tab: tab = state(type=tab)
    selected = attr(default=False)


class tabs(Tag, name='tabs'):
    dark_theme = attr(default=False)
    selected_id = attr(type=str)
    selected: tab = state(type=tab)

    name: str = 'Unknown'

    default_style = Style(
        styles={
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
        },
    )

    children = [
        tabs_titles := ul(),
    ]

    @property
    def tabs_list(self) -> dict[str, tab]:
        # TODO: make tabs_list one-time calculated attribute
        return {name: _tab for name, _tab in self.ref_children.items() if isinstance(_tab, tab)}

    @classmethod
    def __class_declared__(cls):
        for tab_id, _tab_title in cls.tabs_titles.child.ref_children.items():
            _tab_title.on('click')(lambda _ul, _tab_id=tab_id: _ul.parent.select_tab(_tab_id))

    def mount(self):
        for tab_id in self.tabs_list:
            getattr(self.tabs_titles, tab_id)._link_parent_attrs(self)

        url = js.URL.new(js.location.href)

        selected = None
        if url.hash and url.hash.startswith(f'#tab-{self.name}/'):
            selected = self.select_tab(url.hash[len(f'#tab-{self.name}/') :])
            if selected:
                js.location.hash = ''
        if not selected:
            selected = self.select_tab(url.searchParams.get(self.name))
        if not selected:
            self.select_tab(first(self.tabs_titles.ref_children.keys()))
        self._update_url()

    def select_tab(self, tab_id):
        if not tab_id or not hasattr(self, tab_id):
            return

        self.selected_id = tab_id
        if not self.selected or self.selected.tab_id != tab_id:
            for child in self.tabs_list.values():
                child.visible = False
            for title in self.tabs_titles.ref_children.values():
                title.selected = False
            self.selected = getattr(self, tab_id)
            self.selected.visible = True
            getattr(self.tabs_titles, tab_id).selected = True

        self._update_url()
        return self.selected

    def _update_url(self):
        selected_tab = self.selected

        url = js.URL.new(js.location.href)
        if (not url.hash and url.href[-1] == '#') or url.hash == '#':
            url.href = url.href[:-1]
        if url.searchParams.get(self.name) == selected_tab.tab_id:
            return

        url.searchParams.set(self.name, selected_tab.tab_id)  # modifies url.href

        replace_url(url, name=selected_tab.id, title=''.join(getattr(self.tabs_titles, selected_tab.tab_id).content()))


__all__ = ['tab', 'tab_title', 'tabs']
