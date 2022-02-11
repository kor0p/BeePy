# [PYWEB IGNORE START]
from .framework import Tag, attr, const_attr, state, on, ContentType
from .tags import a, ul, div

import js
import pyodide
# [PYWEB IGNORE END]


class tab(Tag, name='tab'):
    id: str = attr()
    href: str = attr()

    name: str = state()
    children_content: ContentType = state()

    title = a()

    def __init__(self, name: str, content: ContentType, href=''):
        super().__init__(id=name, name=name, href=href, children_content=content)

        self.title.href = href
        # self.title.children.append(name)
        self.title.children += [name]

    @on
    def click(self, event):
        self.parent.parent.select_tab(self.id)

    def __render__(self, attrs=None, children=None):
        # self.title.href = self.href
        # self.title.children.append(self.name)
        return super().__render__(attrs=attrs, children=(self.title,))


class tabs(Tag, name='tabs'):
    name: str = const_attr()
    selected_id: str = state()
    selected: tab = state()

    children_tabs: list[tab, ...]

    tabs_list = ul()
    tabs_content = div()

    def __init__(self, name, tabs, selected_id=None):
        super().__init__(name=name, selected_id=selected_id)

        tabs = list(tabs)
        if selected_id is None:
            url = js.URL.new(js.location.href)
            selected_id = url.searchParams.get(self.name) or tabs[0].id

        self.children_tabs = tabs
        self.tabs_list.children = self.children_tabs
        self.tabs_content.children = [
            child.children_content for child in self.children_tabs
        ]

        self.select_tab(selected_id)

    def select_tab(self, tab_id):
        self.selected_id = tab_id
        if not self.selected or self.selected.id != tab_id:
            self.selected = self.find_tab(id=self.selected_id)
            self._update_url()

    def find_tab(self, **tab_attrs):
        result = None

        for _tab in self.children_tabs:
            for attr_name, attr_value in tab_attrs.items():
                if getattr(_tab, attr_name) != attr_value:
                    continue
                result = _tab
                break
            else:  # no break
                continue
            break

        return result

    def _update_url(self):
        selected_tab = self.selected

        url = js.URL.new(js.location.href)
        if url.searchParams.get(self.name) == selected_tab.id:
            return

        url.searchParams.set(self.name, selected_tab.id)  # modifies url.href

        js.history.pushState(
            pyodide.to_js({
                'name': f'{self.name}:{selected_tab.name}',
            }),
            selected_tab.name,
            url.href,
        )

    def render(self):
        self._update_url()
