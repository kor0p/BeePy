import re
import string
import random
import builtins
import inspect
import traceback
from functools import wraps
from typing import Any

import js
import pyodide


log = js.console
NONE_TYPE = type(None)
__CONFIG__ = {
    'debug': True,
    'modules': [],
}


_current_render: list['Renderer', ...] = []
_current_rerender: list['Renderer', ...] = []
_current__lifecycle_method: dict[str, dict[int, 'Tag']] = {}
_current: dict[str, Any] = {
    'render': _current_render,
    'rerender': _current_rerender,
    '_lifecycle_method': _current__lifecycle_method,
}


def _debugger(error=None):
    log.warn('\n'.join(traceback.format_stack()[0 if error else 5:]))
    js._locals = pyodide.to_js(inspect.currentframe().f_back.f_locals, dict_converter=js.Object.fromEntries)
    js._DEBUGGER(error)


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
    return re.sub(
        r'([A-Z])',
        lambda m: '-' + m.group(1).lower(),
        re.sub('[_ ]', '-', name)
    ).strip('-')


def js_func(once=False):
    if once:
        create_proxy = pyodide.create_once_callable
    else:
        create_proxy = pyodide.create_proxy

    return create_proxy


def js_await(to_await):
    """
    JS await can resolve both: coroutines and raw value
    """
    js.pyweb._to_await = to_await
    return js.eval('''
(async () => {
    const r = await window.pyweb._to_await
    delete window.pyweb._to_await
    return r
})()
''')


def to_sync(function):
    """
    Using JS await from python, we can synchronously get result of coroutine
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        return js_await(function(*args, **kwargs))
    return wrapper


async def delay(ms):
    return await js.delay(ms)


@to_sync
async def sleep(s):
    return await js.delay(s * 1000)


_all_globals = builtins.__dict__
_globals = {}
_allowed_globals = (
    '__name__', 'abs', 'all', 'any', 'ascii', 'bin', 'breakpoint', 'callable', 'chr', 'delattr', 'dir', 'divmod',
    'format', 'getattr', 'hasattr', 'hash', 'hex', 'id', 'input', 'isinstance', 'issubclass', 'iter', 'len', 'max',
    'min', 'next', 'oct', 'ord', 'pow', 'print', 'repr', 'round', 'setattr', 'sorted', 'sum', 'vars', 'None',
    'Ellipsis', 'False', 'True', 'bool', 'memoryview', 'bytearray', 'bytes', 'complex', 'dict', 'enumerate', 'filter',
    'float', 'frozenset', 'int', 'list', 'map', 'object', 'range', 'reversed', 'set', 'slice', 'str', 'tuple', 'type',
    'zip',
)
for key, value in _all_globals.items():
    if key in _allowed_globals:
        _globals[key] = value


def safe_eval(code, _locals=None):
    if _locals is None:
        _locals = {}

    return eval(code, _globals, _locals)


__all__ = [
    'log', 'NONE_TYPE', '__CONFIG__', '_current', '_debugger', 'get_random_name', 'to_kebab_case', 'js_func', 'js_await', 'to_sync',
    'delay', 'sleep', 'safe_eval',
]
