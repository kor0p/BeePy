import re
import string
import random

_w = string.ascii_letters + string.digits + '_'


def get_random_name(length=10):
    """https://stackoverflow.com/a/23728630/2213647"""
    return ''.join(
        random.SystemRandom().choice(_w)
        for _ in range(length)
    )


def to_kebab_case(name: str):
    """
    parsing name of tag to html-compatible or name of property to css-compatible
    >>> class __pyweb__(Tag): ...  # <pyweb></pyweb>
    >>> class myTagName(Tag): ...  # <my-tag-name/>
    >>> style(font_size='20px')  # font-size: 20px
    >>> style(backgroundColor='red')  # background-color: red
    """
    name = name.strip('_')
    name = re.sub('_', '-', name)
    name = re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), name)
    return name
