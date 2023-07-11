from __future__ import annotations

import inspect
from typing import Optional, Any, Callable
from types import MethodType
from functools import partial, wraps
from copy import deepcopy

from beepy.types import Tag
from beepy.utils import js, to_js
from beepy.utils.js_py import create_proxy
from beepy.utils.internal import _PY_TAG_ATTRIBUTE


GLOBAL_EVENTS_LIST = ('keyup', 'keypress', 'keydown')
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


# TODO: click.(right|middle) ; click.left ; etc.


def key_code_check(key_name, event):
    return event.keyCode in _key_codes[key_name]


RAW_JS_CHECKS = ('prevent', 'stop', 'stop_all')


class on:
    __slots__ = ('name', 'callback', 'get_parent', 'modifiers', 'checks', 'js_checks')

    name: Optional[str]
    callback: Callable[[Tag, ...], Any]
    get_parent: bool
    modifiers: list[str]
    checks: list[Callable[[js.Event], bool]]
    js_checks: list[str]

    def __init__(self, method):
        self.get_parent = False
        self.modifiers = []
        self.checks = []
        self.js_checks = []

        if isinstance(method, str):
            if '.' in method:
                method, *self.modifiers = method.split('.')
                for modifier in self.modifiers:
                    if modifier in _key_codes:
                        # TODO: check for visibility?
                        self.checks.append(partial(key_code_check, modifier))
                    elif modifier in RAW_JS_CHECKS:
                        self.js_checks.append(modifier)
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
        if instance is None:
            return self
        return self.callback

    def _prepare_call(self, tag, event):
        for check in self.checks:
            if not check(event):
                return

        if self.get_parent:
            tag = tag.parent

        if isinstance(self.callback, MethodType):
            return self.callback, tag
        else:
            return MethodType(self.callback, tag), tag

    async def _a_call(self, tag, event):
        if (prepare := self._prepare_call(tag, event)) is None:
            return

        fn, tag = prepare

        data = await fn(event)
        self._after_call(tag, event)
        return data

    def _call(self, tag, event):
        if (prepare := self._prepare_call(tag, event)) is None:
            return

        fn, tag = prepare
        data = fn(event)
        self._after_call(tag, event)
        return data

    def _after_call(self, tag, event):
        for dependent in tag._dependents:
            # TODO: move to other place
            dependent.__render__()

        getattr(event.currentTarget, _PY_TAG_ATTRIBUTE, tag).__render__()

    def _make_listener(self, event_name: str, tag: Tag):
        if inspect.iscoroutinefunction(self.callback):
            @wraps(self.callback)
            async def method(event):
                return await self._a_call(tag, event)
        else:
            @wraps(self.callback)
            def method(event):
                return self._call(tag, event)
        is_global = event_name in GLOBAL_EVENTS_LIST  # TODO: check this || what about set global by attr?
        return js.beepy.addAsyncListener(
            js.document if is_global else tag.mount_element, event_name, create_proxy(method), to_js(self.js_checks)
        )

    @classmethod
    def _remove_listener(cls, event_name: str, tag: Tag, event_listener: Callable):
        is_global = event_name in GLOBAL_EVENTS_LIST

        (js.document if is_global else tag.mount_element).removeEventListener(event_name, event_listener)

    def __set__(self, instance, value):
        raise AttributeError(f'Cannot set on_{self.name} event handler')

    def __delete__(self, instance):
        pass

    def __set_name__(self, owner, name, *, set_static_listeners=True):
        if self.name is None:
            self.name = name

        if set_static_listeners:
            owner._static_listeners = deepcopy(owner._static_listeners)
            owner._static_listeners[self.name].append(self)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


__all__ = ['on', '_key_codes', 'RAW_JS_CHECKS']
