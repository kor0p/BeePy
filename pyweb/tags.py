from typing import Callable, Any

# [PYWEB IGNORE START]
from .framework import Tag, attr, state, html_attr, html_state, on
# [PYWEB IGNORE END]


class div(Tag, name='div', content_tag=None):
    pass


class a(div, name='a'):
    href: str = attr()


class p(div, name='p'):
    pass


class ul(div, name='ul'):
    pass


class li(div, name='li'):
    pass


class option(div, name='option'):
    value = html_attr()
    label: str = html_state()
    defaultSelected: bool = html_state()
    selected: bool = html_state()

    def content(self) -> str:
        return self.label


class select(div, name='select'):
    onchange: Callable[[Tag, Any], None] = state()

    @on
    def change(self, event):
        self.onchange(event.target.value)

    @classmethod
    def with_items(cls, items: dict[str, Any], selected=None, **kwargs):
        return cls(*(
            option(label=label, value=value, defaultSelected=selected == value)
            for value, label in items.items()
        ), **kwargs)


# TODO: add all HTML tags


br = '<br/>'
