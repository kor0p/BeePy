from __future__ import annotations

from typing import Optional, Any, Callable
from types import MethodType
from functools import partial, wraps
from copy import deepcopy

import js

from .types import Tag
from .utils import log, _PY_TAG_ATTRIBUTE, ensure_sync, _current, _debugger, add_event_listener

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


def stop_propagation(event):
    event.stopPropagation()


def prevent_default(event):
    event.preventDefault()


_checks = {
    'prevent': prevent_default,
    'stop': stop_propagation,
}


class on:
    __slots__ = ('name', 'callback', 'get_parent', 'modifiers', 'checks')

    name: Optional[str]
    callback: Callable[[Tag, ...], Any]
    get_parent: bool
    modifiers: list[str, ...]
    checks: list[Callable[[js.Event], bool], ...]

    def __init__(self, method):
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

        data = ensure_sync(fn(event))

        _current['rerender'] = []
        for dependent in tag._dependents:
            if dependent in _current['rerender']:
                continue
            # TODO: move to other place
            log.debug('[_CALL]', 1, fn, dependent)
            dependent.__render__()
        _current['rerender'] = []

        if PY_TAG := getattr(event.currentTarget, _PY_TAG_ATTRIBUTE):
            log.debug('[_CALL]', 2, PY_TAG)
            PY_TAG.__render__()
        else:
            log.debug('[_CALL]', 3, fn)
            tag.__render__()

        return data

    def _make_listener(self, event_name: str, tag: Tag):
        @wraps(self.callback)
        def method(event):
            try:
                return self._call(tag, event)
            except Exception as error:
                log.debug(event_name)  # make available for debugging
                _debugger(error)

        is_global = event_name in ('keyup', 'keypress', 'keydown')  # TODO: check this || what about set global by attr?
        add_event_listener(js.document if is_global else tag.mount_element, event_name, method)
        return method

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
        log.debug('[__SET_NAME__]', self, owner)

    def __repr__(self):
        return f'on_{self.name}({self.callback})'


__all__ = ['on', '_key_codes', '_checks']
