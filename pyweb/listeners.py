from __future__ import annotations

from typing import Optional, Any, Callable
from types import MethodType

import pyodide

from .types import Tag
from .utils import log, js_func, js_await, _current, _debugger


class on:
    __slots__ = ('_proxies', 'name', 'callback', 'get_parent')

    _proxies: list[pyodide.JsProxy]
    name: Optional[str]
    callback: Callable[[Tag, ...], Any]
    get_parent: bool

    def __init__(self, method):
        self._proxies = []
        self.get_parent = False

        if isinstance(method, str):
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

    def _add_listener(self, event_name: str, tag: Tag):
        @js_func()
        def method(event):
            try:
                return self._call(tag, event)
            except Exception as error:
                log.debug(event_name)  # make available for debugging
                _debugger(error)

        self._proxies.append(method)
        tag.mount_element.addEventListener(event_name, method)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

    def __del__(self):
        if not pyodide.IN_BROWSER:
            return
        for proxy in self._proxies:
            proxy.destroy()

    def __set_name__(self, owner, name):
        if self.name is None:
            self.name = name

        owner.listeners[self.name].append(self)
        log.debug('[__SET_NAME__]', self, owner)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


__all__ = ['on']
