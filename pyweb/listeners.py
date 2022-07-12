from __future__ import annotations

from typing import Optional, Any, Callable
from types import MethodType
from functools import partial

import js
import pyodide

from .types import Tag
from .utils import log, js_func, js_await, _current, _debugger


_key_codes = {
    'esc': (27,),
    'tab': (9,),
    'enter': (13,),
    'space': (32,),
    'up': (38,),
    'left': (37,),
    'right': (39,),
    'down': (40,),
    'delete': (8, 46),
}


def key_code_check(key_name, event):
    return event.keyCode in _key_codes[key_name]


def prevent_default(event):
    event.preventDefault()
    return True


_checks = {
    'prevent': prevent_default,
}


class on:
    __slots__ = ('_proxies', 'name', 'callback', 'get_parent', 'modifiers', 'checks')

    _proxies: list[pyodide.JsProxy]
    name: Optional[str]
    callback: Callable[[Tag, ...], Any]
    get_parent: bool
    modifiers: list[str, ...]
    checks: list[Callable[[js.Event], bool], ...]

    def __init__(self, method):
        self._proxies = []
        self.get_parent = False
        self.modifiers = []
        self.checks = []

        if isinstance(method, str):
            if '.' in method:
                method, *self.modifiers = method.split('.')
                for modifier in self.modifiers:
                    if modifier in _key_codes:
                        # TODO: check for visibility?
                        self.checks.append(partial(key_code_check, modifier))
                    elif modifier in _checks:
                        self.checks.append(_checks[modifier])
                    else:
                        raise ValueError(f'Unknown event modifier ".{modifier}"!')

            self.name = method
            return

        self.name = None
        self(method)

    def __call__(self, method, get_parent=None):
        self.callback = method
        self.get_parent = get_parent
        return self

    def __get__(self, instance, owner=None):
        log.debug('[ON]', self, instance, owner)
        if instance is None:
            return self
        return self.callback

    def _call(self, tag, event):
        for check in self.checks:
            if not check(event):
                return

        if self.get_parent:
            tag = tag.parent
        if isinstance(self.callback, MethodType):
            fn = self.callback
        else:
            fn = MethodType(self.callback, tag)

        data = js_await(fn(event))

        _current['rerender'] = []
        for dependent in tag._dependents:
            if dependent in _current['rerender']:
                continue
            # TODO: move to other place
            log.debug('[_CALL]', 1, fn, dependent)
            dependent.__render__()
        _current['rerender'] = []

        if hasattr(event.currentTarget, '_py'):
            log.debug('[_CALL]', 2, event.currentTarget._py)
            event.currentTarget._py.__render__()
        else:
            log.debug('[_CALL]', 3, fn)
            tag.__render__()

        return data

    def _make_listener(self, event_name: str, tag: Tag):
        @js_func()
        def method(event):
            try:
                return self._call(tag, event)
            except Exception as error:
                log.debug(event_name)  # make available for debugging
                _debugger(error)
        method: pyodide.JsProxy

        self._proxies.append(method)
        method.__on__ = self
        method.__qualname__ = self.callback.__qualname__

        is_global = event_name in ('keyup', 'keypress', 'keydown')  # TODO: check this || what about set global by attr?
        (js.document if is_global else tag.mount_element).addEventListener(event_name, method)
        return method

    def _unlink_listener(self, proxy: pyodide.JsProxy):
        self._proxies.remove(proxy)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

    def __del__(self):
        if not pyodide.IN_BROWSER:
            return
        for proxy in self._proxies:
            proxy.destroy()

    def __set_name__(self, owner, name, *, set_static_listeners=True):
        if self.name is None:
            self.name = name

        if set_static_listeners:
            owner.static_listeners = owner.static_listeners.copy()
            owner.static_listeners[self.name] = owner.static_listeners[self.name].copy()
            owner.static_listeners[self.name].append(self)
        log.debug('[__SET_NAME__]', self, owner)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


__all__ = ['on', '_key_codes', '_checks']
