from functools import wraps

try:
    import js  # reference to window (globalThis), made by pyodide module
except ModuleNotFoundError:
    from . import js

    js.window = js.self = js.globalThis = js

from pyodide.ffi import IN_BROWSER, create_once_callable, create_proxy
from pyodide.ffi import to_js as pyodide_to_js

if IN_BROWSER:
    from pyodide.ffi.wrappers import (
        add_event_listener,
        clear_interval,
        clear_timeout,
        remove_event_listener,
        set_interval,
        set_timeout,
    )
else:
    from .js import add_event_listener, clear_interval, clear_timeout, remove_event_listener, set_interval, set_timeout

log = js.console


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
    js.history.pushState(to_js({'href': url.href} | url_state), unused, url.href)


def replace_url(url, unused='', **url_state):
    js.history.replaceState(to_js({'href': url.href} | url_state), unused, url.href)


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
