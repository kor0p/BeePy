from typing import Any

import js

from .framework import Tag, attr, html_attr


class html_tag(Tag, _root=True, content_tag=None):
    _class = attr()


class div(html_tag, name='div', content_tag=None):
    pass


class hr(html_tag, name='hr'):
    pass


class a(html_tag, name='a'):
    href: str = attr()


class p(html_tag, name='p'):
    pass


class ul(html_tag, name='ul'):
    pass


class li(html_tag, name='li'):
    pass


class span(html_tag, name='span'):
    pass


class _input(html_tag, name='input'):
    type = attr(
        'text',
        enum=(
            'button', 'checkbox', 'color', 'date', 'datetime-local', 'email', 'file', 'hidden', 'image', 'month',
            'number', 'password', 'radio', 'range', 'reset', 'search', 'submit', 'tel', 'text', 'time', 'url', 'week',
        ),
    )
    hidden: bool = attr()
    value = html_attr()

    def clear(self):
        self.value = ''


class button(html_tag, name='button'):
    type = attr('button', enum=('submit', 'reset', 'button'))


class option(html_tag, name='option'):
    value = html_attr()
    label: str = html_attr()
    defaultSelected: bool = html_attr()
    selected: bool = html_attr()


class select(html_tag, name='select'):
    @classmethod
    def with_items(cls, items: dict[str, Any], selected=None, **kwargs):
        return cls(*(
            option(label=label, value=value, defaultSelected=selected == value)
            for value, label in items.items()
        ), **kwargs)


class StandaloneTag(html_tag, _root=True):
    def clone(self):
        raise ValueError(f'Coping or using as child is not allowed for StandaloneTag("{self._tag_name_}")')


class Head(StandaloneTag, name='head', mount=js.document.head):
    pass


class Body(StandaloneTag, name='body', mount=js.document.body):
    pass


# TODO: add all HTML tags


br = '<br/>'


__all__ = ('html_tag', 'div', 'a', 'p', 'ul', 'li', 'span', '_input', 'button', 'option', 'select', 'Head', 'br')
