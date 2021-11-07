import re
import string
import random

_w = string.ascii_uppercase + string.ascii_lowercase + string.digits + '_'


def get_random_name(length=10):
    """https://stackoverflow.com/a/23728630/2213647"""
    return ''.join(
        random.SystemRandom().choice(_w)
        for _ in range(length)
    )


def camel_or_snake_to_kebab_case(string: str):
    """
    parsing name of tag to html-compatible or name of property to css-compatible
    >>> class __pyx__(): ...  # <pyx></pyx>
    >>> class myTagName(): ...  # <my-tag-name/>
    >>> style(font_size='20px')  # font-size: 20px
    >>> style(backgroundColor='red')  # background-color: red
    """
    string = re.sub('_', '-', string)
    string = re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), string)
    return string
