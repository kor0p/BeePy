import inspect
import math
import re
import string

from boltons.typeutils import make_sentinel

from beepy.utils.internal import rnd

NONE_TYPE = type(None)
MISSING = make_sentinel(var_name='MISSING')


def log10_ceil(num):
    return math.ceil(math.log10(num or 1)) or 1


def wraps_with_name(name):
    def wrapper(func):
        func.__name__ = func.__qualname__ = name
        return func

    return wrapper


def _internal_to_kebab_case(name: str, *, replacer='-'):
    return re.sub(
        r'(?P<upper>[A-Z])', lambda m: replacer + m.group('upper').lower(), re.sub('[_ ]', replacer, name.strip('_ '))
    ).strip(replacer)


def to_kebab_case(name: str, *, replacer='-'):
    """
    Converts name of tag to html-compatible or name of property to css-compatible

    >>> class __beepy__(Tag): ...  # <beepy></beepy>
    >>> class myTagName(Tag): ...  # <my-tag-name/>
    >>> Style(font_size='20px')  # font-size: 20px
    >>> Style(backgroundColor='red')  # background-color: red
    """
    if hasattr(name, '__html__'):
        return name.__html__()
    return _internal_to_kebab_case(name, replacer=replacer)


def escape_html(s, *, quote=False, whitespace=False):
    """Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is True (default), the quotation mark characters (" and ') are also translated.
    If the optional flag whitespace is True, new line (\n) and tab (\t) characters are also translated.
    """
    #       Must be done first!
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if quote:
        s = s.replace('"', '&quot;').replace("'", '&#39;')
    if whitespace:
        s = s.replace('\n', '<br>').replace('\t', '&emsp;').replace('  ', ' &nbsp;')
    return s


_w = string.ascii_letters + string.digits + '_'


def get_random_name(length=6):
    return ''.join(rnd.choice(_w) for _ in range(length))


def safe_issubclass(type_or_Any, class_or_tuple_to_check):
    try:
        return issubclass(type_or_Any, class_or_tuple_to_check)
    except TypeError:
        return False


class AnyOfType:
    __slots__ = ('type',)

    def __init__(self, type):
        self.type = type

    def __eq__(self, other):
        return isinstance(other, self.type)

    def __repr__(self):
        return f'AnyOfType<{self.type}>'

    def __hash__(self):
        return hash(self.type)


class Locker:
    __slots__ = ('name', 'locked')

    def __init__(self, name='Lock'):
        self.name = name
        self.locked = False

    def __enter__(self):
        self.locked = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.locked = False

    def __bool__(self):
        return self.locked

    def __str__(self):
        return f'Locker<{self.name}>({self.locked})'


def call_handler_with_optional_arguments(handler, obj, optional_args, *args):
    parameters = inspect.signature(handler).parameters

    for name, arg in reversed(optional_args.items()):
        if name in parameters:
            args = (arg, *args)
    return handler(obj, *args)


def nested_copy(dct):
    # We shouldn't use deepcopy, we want just copy nested dicts, not objects inside
    return {key: value.copy() for key, value in dct.items()}


__all__ = [
    'NONE_TYPE',
    'log10_ceil',
    'escape_html',
    'wraps_with_name',
    'get_random_name',
    'to_kebab_case',
    'safe_issubclass',
    'AnyOfType',
    'Locker',
    'call_handler_with_optional_arguments',
    'nested_copy',
]
