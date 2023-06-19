from http.client import HTTPException
import inspect
import dataclasses
import json
import math
import re
import sys
import string
import random
# TODO: add some param to use shadow root directlyimport inspect
import traceback
import asyncio
from functools import wraps
from typing import Any
from datetime import datetime
from importlib import import_module

import js
import micropip
from pyodide import http as pyodide_http
import beepy


# TODO: make it a module (could be a quite complicated due to loading beepy modules as /<file>.py requests)


try:
    from pyodide.ffi import IN_BROWSER, create_once_callable, create_proxy, to_js as pyodide_to_js
except ImportError:
    from pyodide import IN_BROWSER, create_once_callable, create_proxy, to_js as pyodide_to_js
    js.console.log('FutureWarning: You need to upgrade pyodide version to 0.21.0 or higher')


class UpgradedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime):
            return o.strftime(__CONFIG__['default_datetime_format'])
        return super().default(o)


def to_js(obj, dict_converter=js.Object.fromEntries, **kwargs):
    return pyodide_to_js(obj, dict_converter=dict_converter, **kwargs)


log = js.console
NONE_TYPE = type(None)
_PY_TAG_ATTRIBUTE = '__PYTHON_TAG__'
__CONFIG__ = {
    'debug': False,
    'style_head': True,
    'api_url': '/',
    'default_datetime_format': '%Y-%m-%dT%H:%M:%S.%f%Z',
    'inputs_auto_id': True,
    'html_replace_whitespaces': True,
    'modules': [],
    'requirements': [],
}

if 1 == 1:
    __CONFIG__['debug'] = True


def merge_configs():
    __CONFIG__.update(js.beepy.__CONFIG__.to_py())
    js.beepy.__CONFIG__ = to_js(__CONFIG__)


if IN_BROWSER:  # TODO: check support for non-browser runs
    merge_configs()


def _debugger(error=None):
    if isinstance(error, Exception):
        log.warn(traceback.format_exc())
    else:
        log.warn(''.join(traceback.format_stack()[:-1]))
        log.warn(error)
    frame = inspect.currentframe().f_back
    js._locals = to_js(frame.f_locals)
    js._locals._frame = frame
    js._DEBUGGER(error)


def log10_ceil(num):
    return math.ceil(math.log10(num or 1)) or 1


def wraps_with_name(name):
    def wrapper(func):
        func.__name__ = func.__qualname__ = name
        return func
    return wrapper


def escape_html(s, quote=False, whitespace=False):
    """ Replace special characters "&", "<" and ">" to HTML-safe sequences.
        If the optional flag quote is True (default), the quotation mark characters (" and ') are also translated.
        If the optional flag whitespace is True, new line (\n) and tab (\t) characters are also translated.
    """
    #       Must be done first!
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if quote:
        s = s.replace('"', '&quot;').replace('\'', '&#39;')
    if whitespace:
        s = s.replace('\n', '<br>').replace('\t', '&emsp;').replace('  ', ' &nbsp;')
    return s


_w = string.ascii_letters + string.digits + '_'


def get_random_name(length=6):
    return ''.join(
        random.choice(_w)
        for _ in range(length)
    )


def to_kebab_case(name: str, *, replacer='-'):
    """
    parsing name of tag to html-compatible or name of property to css-compatible
    >>> class __beepy__(Tag): ...  # <beepy></beepy>
    >>> class myTagName(Tag): ...  # <my-tag-name/>
    >>> Style(font_size='20px')  # font-size: 20px
    >>> Style(backgroundColor='red')  # background-color: red
    """
    return re.sub(
        r'(?P<upper>[A-Z])',
        lambda m: replacer + m.group('upper').lower(),
        re.sub('[_ ]', replacer, name)
    ).strip(replacer)


def _need_update(old_func, old_name='', *, version):
    old_name = old_name or ('beepy.utils.' + to_kebab_case(old_func.name, replacer='_'))

    @wraps(old_func)
    def _wrapper(*args, **kwargs):
        log.warn(
            f'FutureWarning: function {old_name} is slightly wrapped for old versions of pyodide. '
            f'You need to upgrade pyodide version to {version} or higher'
        )
        new_args = []
        for arg in args:
            if callable(arg):
                arg = create_once_callable(arg)
            new_args.append(arg)
        return old_func(*new_args, **kwargs)

    return _wrapper


try:
    from pyodide.ffi.wrappers import (
        set_timeout, clear_timeout, set_interval, clear_interval, add_event_listener, remove_event_listener,
    )
except ImportError:
    set_timeout = _need_update(js.setTimeout, version='0.21.0')
    clear_timeout = _need_update(js.clearTimeout, version='0.21.0')
    set_interval = _need_update(js.setInterval, version='0.21.0')
    clear_interval = _need_update(js.clearInterval, version='0.21.0')
    add_event_listener = _need_update(js.addEventListener, version='0.21.0')
    remove_event_listener = _need_update(js.removeEventListener, version='0.21.0')


class const_attribute(property):
    def __set__(self, instance, value):
        if self.__get__(instance) is None:
            super().__set__(instance, value)
        else:
            raise AttributeError


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


async def request(url, method='GET', body=None, headers=None, **opts):
    if body is not None:
        body = json.dumps(body, cls=UpgradedJSONEncoder)

    if headers is None:
        headers = {}

    headers.update({
        'mode': 'no-cors',
        'Content-Type': 'application/json',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Origin': '*',
    })

    response = await pyodide_http.pyfetch(
        __CONFIG__['api_url'] + url, method=method, body=body, headers=headers, **opts
    )

    if int(response.status) >= 400:
        raise HTTPException(response.status)

    if method == 'GET' or opts.get('to_json'):
        response = await response.json()
    else:
        response = await response.string()

    return response


if not IN_BROWSER:
    import requests

    async def request(url, method='GET', body=None, headers=None, **opts):
        if body is not None:
            body = json.dumps(body, cls=UpgradedJSONEncoder)

        if headers is None:
            headers = {}

        # TODO: check opts argument compatibility

        response = requests.request(
            method, __CONFIG__['api_url'] + url, data=body, headers=headers,
        )

        if int(response.status_code) >= 400:
            raise HTTPException(response.status_code)

        if method == 'GET' or opts.get('to_json'):
            response = response.json()
        else:
            response = response.text

        return response


def ensure_sync(to_await, callback=lambda x: x):
    if inspect.iscoroutine(to_await):
        task = asyncio.get_event_loop().run_until_complete(to_await)
        task.add_done_callback(callback)
        return task

    callback(to_await)
    return to_await


def force_sync(function):
    # TODO: maybe do it with class will be better?

    callbacks = []

    @wraps(function)
    def wrapper(*args, _done_callback_=None, **kwargs):
        current_callbacks = [(cb() if dynamic else cb) for cb, dynamic in callbacks]
        current_callbacks.append(_done_callback_)

        def _callback(_res_):
            try:
                r = _res_.result()
            except Exception as e:
                _debugger(e)
                return

            for cb in current_callbacks:
                if cb is None:
                    continue
                try:
                    cb(*args, **kwargs, _res_=r)
                except Exception as e:
                    _debugger(e)
        return ensure_sync(function(*args, **kwargs), _callback)

    wrapper.run_after = wrapper.add_callback = lambda fn: callbacks.append((fn, False)) or fn
    wrapper.add_dynamic_callback = lambda fn: callbacks.append((fn, True)) or fn

    return wrapper


def force_sync__wait_load(function):
    wrapper = force_sync(function)
    wrapper.add_dynamic_callback(beepy.context.Context.create_onload)
    return wrapper


force_sync.wait_load = force_sync__wait_load


delay = js.delay


@force_sync
async def sleep(s):  # TODO: check if this actually works or not
    return await js.delay(s * 1000)


class Interval:
    __slots__ = ('_id',)

    def __init__(self, function, args=None, kwargs=None, period=0):
        @wraps(function)
        def _callback():
            return function(*(args or ()), **(kwargs or {}))

        self._id = set_interval(_callback, period * 1000)

    def clear(self):
        return clear_interval(self._id)


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


async def reload_requirements():
    get_requirements = __CONFIG__['requirements']
    if not callable(get_requirements):  # static requirements, must be already loaded
        return

    await asyncio.gather(*[
        micropip.install(requirement)
        for requirement in get_requirements()
    ])


def push_url(url, unused='', **url_state):
    js.history.pushState(to_js({'href': url.href, **url_state}), unused, url.href)


def replace_url(url, unused='', **url_state):
    js.history.replaceState(to_js({'href': url.href, **url_state}), unused, url.href)


def lazy_import(module_path):
    if not (
        (module := sys.modules.get(module_path))
        and (spec := getattr(module, "__spec__", None))
        and getattr(spec, "_initializing", False) is False
    ):
        module = import_module(module_path)

    return module


def import_string(dotted_path):
    module_path, class_name = dotted_path.rsplit('.', 1)
    return getattr(lazy_import(module_path), class_name)


def lazy_import_cls(cls):
    if isinstance(cls, str):
        return import_string(cls)
    return cls


class _BeePyGlobals(dict):
    def __getitem__(self, key):
        result = super().__getitem__(key)
        for handler in __beepy_global_handlers__:
            result = handler(self, key, result)
        return result


def _default_global_handlers(locals_dict, key, result):
    if key.startswith('_p__'):
        return result(locals_dict)
    return result


__beepy_global_handlers__ = [_default_global_handlers]


__all__ = [
    'IN_BROWSER', 'create_once_callable', 'create_proxy', 'to_js',
    'log', '_PY_TAG_ATTRIBUTE', 'NONE_TYPE', '__CONFIG__', '_debugger',
    'log10_ceil', 'wraps_with_name', 'get_random_name', 'to_kebab_case',
    'set_timeout', 'clear_timeout', 'set_interval', 'clear_interval', 'add_event_listener', 'remove_event_listener',
    'const_attribute', 'ensure_sync', 'force_sync', 'delay', 'sleep',
    'lazy_import', 'import_string', 'lazy_import_cls', 'safe_issubclass', 'reload_requirements',
]
