# [PYWEB IGNORE START]
from .framework import Tag, attr
# [PYWEB IGNORE END]


class div(Tag, name='div', content_tag=None):
    pass


class a(div, name='a'):
    href: str = attr()


class ul(div, name='ul'):
    pass


class li(div, name='li'):
    pass


# TODO: add all HTML tags


br = '<br/>'
