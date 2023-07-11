from functools import wraps

try:
    import js  # reference to window (globalThis), made by pyodide module
except ModuleNotFoundError:
    from . import js

from beepy.utils.common import to_kebab_case


log = js.console


try:
    from pyodide.ffi import IN_BROWSER, create_once_callable, create_proxy, to_js as pyodide_to_js
except ImportError:
    from pyodide import IN_BROWSER, create_once_callable, create_proxy, to_js as pyodide_to_js

    if IN_BROWSER:
        log.log('FutureWarning: You need to upgrade pyodide version to 0.21.0 or higher')


def _need_update(old_func, old_name='', *, version):
    old_name = old_name or ('beepy.utils.js_py.' + to_kebab_case(old_func.name, replacer='_'))

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
        set_timeout,
        clear_timeout,
        set_interval,
        clear_interval,
        add_event_listener,
        remove_event_listener,
    )
except ImportError:
    set_timeout = _need_update(js.setTimeout, version='0.21.0')
    clear_timeout = _need_update(js.clearTimeout, version='0.21.0')
    set_interval = _need_update(js.setInterval, version='0.21.0')
    clear_interval = _need_update(js.clearInterval, version='0.21.0')
    add_event_listener = _need_update(js.addEventListener, version='0.21.0')
    remove_event_listener = _need_update(js.removeEventListener, version='0.21.0')


class Interval:
    __slots__ = ('_id',)

    def __init__(self, function, args=None, kwargs=None, period=0):
        @wraps(function)
        def _callback():
            return function(*(args or ()), **(kwargs or {}))

        self._id = set_interval(_callback, period * 1000)

    def clear(self):
        return clear_interval(self._id)


def to_js(obj, dict_converter=js.Object.fromEntries, **kwargs):
    return pyodide_to_js(obj, dict_converter=dict_converter, **kwargs)


def push_url(url, unused='', **url_state):
    js.history.pushState(to_js({'href': url.href, **url_state}), unused, url.href)


def replace_url(url, unused='', **url_state):
    js.history.replaceState(to_js({'href': url.href, **url_state}), unused, url.href)


__all__ = [
    'js',
    'IN_BROWSER',
    'create_once_callable',
    'create_proxy',
    'set_timeout',
    'clear_timeout',
    'set_interval',
    'clear_interval',
    'add_event_listener',
    'remove_event_listener',
    'Interval',
    'to_js',
    'push_url',
    'replace_url',
]
