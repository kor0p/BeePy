from typing import Any, Optional

from beepy.framework import Tag
from beepy.attrs import attr, state, html_attr
from beepy.children import Children
from beepy.utils import js, __CONFIG__
from beepy.utils.common import get_random_name, AnyOfType


AUTO_ID = object()


class html_tag(Tag, _root=True, content_tag=None):
    contenteditable = html_attr(type=bool)
    id = html_attr(type=str)
    class_ = html_attr(type=str)

    def __set_ref__(self, parent, ref):
        super().__set_ref__(parent, ref)
        if type(self).id is html_tag.id and (
            self.id is AUTO_ID or (__CONFIG__['inputs_auto_id'] and self.id is None)
        ):
            # TODO: replace 5 and 2 with some log value
            self.id = f'{ref.name or get_random_name(5)}-{get_random_name(2)}'


def by__input_id(input_tag):
    return input_tag.id.rsplit('-', 1)[0]


def by__ref(tag):
    if ref := tag._ref:
        return ref.name


class div(html_tag, name='div', content_tag=None):
    pass


class hr(html_tag, name='hr'):
    pass


class img(html_tag, name='img'):
    src = attr(type=str)


class a(html_tag, name='a'):
    href = attr(type=str)
    target = attr(type=str, enum={'_blank', '_self', '_parent', '_top', AnyOfType(str)})


class p(html_tag, name='p'):
    pass


class b(html_tag, name='b'):
    pass


class i(html_tag, name='i'):
    pass


class ul(html_tag, name='ul'):
    pass


class li(html_tag, name='li'):
    pass


class span(html_tag, name='span'):
    pass


class table(html_tag, name='table'):
    pass


class thead(html_tag, name='thead'):
    pass


class tbody(html_tag, name='tbody'):
    pass


class tr(html_tag, name='tr'):
    pass


class th(html_tag, name='th'):
    pass


class td(html_tag, name='td'):
    pass


class label(html_tag, name='label'):
    for_ = attr(type=str)

    def __set_ref__(self, parent, ref):
        super().__set_ref__(parent, ref)
        if parent and isinstance(self.for_, Tag):
            self.for_ = self.for_._ref.__get__(parent).id


class form(html_tag, name='form'):
    pass


class h1(html_tag, name='h1'):
    pass


class h2(html_tag, name='h2'):
    pass


class h3(html_tag, name='h3'):
    pass


class h4(html_tag, name='h4'):
    pass


class h5(html_tag, name='h5'):
    pass


class h6(html_tag, name='h6'):
    pass


class input_(html_tag, name='input'):
    type = attr(
        'text',
        enum={
            'button', 'checkbox', 'color', 'date', 'datetime-local', 'email', 'file', 'hidden', 'image', 'month',
            'number', 'password', 'radio', 'range', 'reset', 'search', 'submit', 'tel', 'text', 'time', 'url', 'week',
        },
    )
    hidden = attr(False)
    value = html_attr('', model='input')

    def clear(self):
        self.value = ''


class textarea(html_tag, name='textarea'):
    value = html_attr('', model='change')
    data_gramm = html_attr(True, type=str)

    def clear(self):
        self.value = ''


class header(html_tag, name='header'):
    pass


class main(html_tag, name='main'):
    pass


class footer(html_tag, name='footer'):
    pass


class nav(html_tag, name='nav'):
    pass


class button(html_tag, name='button'):
    type = attr('button', type=str, enum={'submit', 'reset', 'button'})


class option(html_tag, name='option'):
    value = html_attr()
    label = html_attr('')
    defaultSelected = html_attr(False)
    selected = html_attr(False)


class select(html_tag, name='select'):
    value = html_attr(model='change')

    children = [
        options := Children(),
    ]

    def select(self, value):
        self.value = value

    @classmethod
    def with_items(cls, items: dict[str, Any], **kwargs):
        return cls(options=[
            option(label=label_, value=value)
            for value, label_ in items.items()
        ], **kwargs)


class StandaloneTag(html_tag, _root=True):
    def __init__(self, *args, **kwargs):
        kwargs['_load_children'] = True
        super().__init__(*args, **kwargs)

    def __mount__(self, element, parent: Tag, index=None):
        # too many copy-paste?
        self.parent = parent
        self.mount_parent = element
        self.pre_mount()

    def clone(self, parent=None):
        return self

    def as_child(self, parent: Optional[Tag], exists_ok=False):
        return super().as_child(parent, True)


class Head(StandaloneTag, name='head', mount=js.document.head):
    title = state()

    def render(self):
        if self.title:
            js.document.title = self.title


Head = Head()


class Body(StandaloneTag, name='body', mount=js.document.body):
    style = html_attr()


Body = Body()


# TODO: add all HTML tags


__all__ = [
    'html_tag', 'div', 'a', 'p', 'b', 'i', 'ul', 'li', 'span', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'input_', 'textarea', 'header', 'main', 'footer', 'nav', 'button', 'option', 'select', 'Head',
]
